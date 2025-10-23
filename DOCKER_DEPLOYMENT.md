# Docker Deployment Guide

## การจัดการไฟล์ใน Docker (File Management in Docker)

แอปพลิเคชันนี้ใช้ไดเรกทอรี 2 ตัวสำหรับจัดเก็บข้อมูล:
- `uploads/` - เก็บไฟล์ CSV ที่ผู้ใช้อัปโหลด
- `static/outputs/` - เก็บกราฟและรายงาน PDF ที่สร้างขึ้น

### วิธีการ Deploy แบบต่างๆ

#### 1. Production Deployment (แนะนำ)

ใช้ Named Volumes สำหรับ production เพื่อความปลอดภัยและประสิทธิภาพที่ดีกว่า:

```bash
# Build และรัน
docker-compose up -d

# ตรวจสอบ volumes
docker volume ls

# ดู logs
docker-compose logs -f

# หยุดและลบ container (ข้อมูลใน volumes จะยังอยู่)
docker-compose down

# ลบทั้ง containers และ volumes (ข้อมูลจะหายทั้งหมด)
docker-compose down -v
```

**ข้อดี:**
- ✅ ข้อมูลจะไม่หายแม้ลบ container
- ✅ ประสิทธิภาพดีกว่า (โดยเฉพาะบน macOS และ Windows)
- ✅ ปลอดภัยกว่า - ไฟล์อยู่ภายใน Docker volume
- ✅ ง่ายต่อการ backup ด้วย docker volume

**การ Backup และ Restore:**

```bash
# Backup uploads
docker run --rm -v solar_cal_ponix_solar-uploads:/data -v $(pwd):/backup \
  alpine tar czf /backup/uploads-backup.tar.gz -C /data .

# Backup outputs
docker run --rm -v solar_cal_ponix_solar-outputs:/data -v $(pwd):/backup \
  alpine tar czf /backup/outputs-backup.tar.gz -C /data .

# Restore uploads
docker run --rm -v solar_cal_ponix_solar-uploads:/data -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/uploads-backup.tar.gz"

# Restore outputs
docker run --rm -v solar_cal_ponix_solar-outputs:/data -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/outputs-backup.tar.gz"
```

#### 2. Development Deployment

ใช้ Bind Mounts สำหรับ development เพื่อเข้าถึงไฟล์บน host ได้ง่าย:

```bash
# ใช้ไฟล์ docker-compose.dev.yml
docker-compose -f docker-compose.dev.yml up -d

# ตรวจสอบว่าไดเรกทอรีถูกสร้างบน host
ls -la uploads/
ls -la static/outputs/
```

**ข้อดี:**
- ✅ เข้าถึงไฟล์บน host ได้ง่าย
- ✅ ดู/ลบไฟล์ได้โดยตรง
- ✅ เหมาะสำหรับการพัฒนาและทดสอบ

**ข้อควรระวัง:**
- ⚠️ Permission issues อาจเกิดขึ้นบน Linux
- ⚠️ ไฟล์จะหายถ้าลบไดเรกทอรีบน host

#### 3. การจัดการไฟล์เก่า

แอปพลิเคชันมี Auto-cleanup ที่จะลบไฟล์เก่ากว่า 24 ชั่วโมงอัตโนมัติ
- ทำงานทุกๆ 6 ชั่วโมง
- ลบทั้งไฟล์ uploads และ outputs ที่เก่ากว่า 24 ชั่วโมง

สามารถลบไฟล์เก่าด้วยตัวเองได้:

```bash
# เข้าไปใน container
docker-compose exec solar-analyzer /bin/bash

# ลบไฟล์ uploads ที่เก่ากว่า 1 วัน
find /app/uploads -type f -mtime +1 -delete

# ลบไฟล์ outputs ที่เก่ากว่า 1 วัน
find /app/static/outputs -type f -mtime +1 -delete

# ออกจาก container
exit
```

### การตรวจสอบและแก้ไขปัญหา

#### ตรวจสอบ Permissions

```bash
# เข้าไปดูสิทธิ์ในไดเรกทอรี
docker-compose exec solar-analyzer ls -la /app/uploads
docker-compose exec solar-analyzer ls -la /app/static/outputs

# ตรวจสอบว่า user ใน container เป็นใคร
docker-compose exec solar-analyzer whoami
# ควรได้ผลลัพธ์เป็น "app"
```

#### แก้ไข Permission Issues

ถ้ามีปัญหาเรื่อง permissions:

```bash
# แก้ไขสิทธิ์ใน container
docker-compose exec -u root solar-analyzer chown -R app:app /app/uploads
docker-compose exec -u root solar-analyzer chown -R app:app /app/static/outputs
docker-compose exec -u root solar-analyzer chmod -R 755 /app/uploads
docker-compose exec -u root solar-analyzer chmod -R 755 /app/static/outputs
```

#### ตรวจสอบ Disk Space

```bash
# ดู disk usage ของ volumes
docker system df -v

# ดูขนาดของแต่ละ volume
docker volume ls
docker run --rm -v solar_cal_ponix_solar-uploads:/data alpine du -sh /data
docker run --rm -v solar_cal_ponix_solar-outputs:/data alpine du -sh /data
```

#### ดู Logs

```bash
# ดู logs ทั้งหมด
docker-compose logs

# ดู logs แบบ real-time
docker-compose logs -f

# ดู logs เฉพาะ cleanup events
docker-compose logs | grep -i "removed"
```

### การย้ายข้อมูล (Migration)

#### จาก Bind Mounts ไป Named Volumes

```bash
# 1. หยุด container เก่า
docker-compose -f docker-compose.dev.yml down

# 2. สร้าง volumes ใหม่และ copy ข้อมูล
docker volume create solar_cal_ponix_solar-uploads
docker volume create solar_cal_ponix_solar-outputs

# 3. Copy ข้อมูลจาก host ไป volume
docker run --rm -v $(pwd)/uploads:/source -v solar_cal_ponix_solar-uploads:/dest \
  alpine sh -c "cd /source && cp -av . /dest/"
  
docker run --rm -v $(pwd)/static/outputs:/source -v solar_cal_ponix_solar-outputs:/dest \
  alpine sh -c "cd /source && cp -av . /dest/"

# 4. รัน production stack
docker-compose up -d
```

### Best Practices

1. **สำหรับ Production:**
   - ✅ ใช้ named volumes (docker-compose.yml)
   - ✅ ตั้ง backup schedule สำหรับ volumes
   - ✅ Monitor disk space
   - ✅ ใช้ health checks

2. **สำหรับ Development:**
   - ✅ ใช้ bind mounts (docker-compose.dev.yml)
   - ✅ เก็บ .gitkeep ไว้ใน git
   - ✅ Ignore ไฟล์จริงใน .gitignore

3. **การรักษาความปลอดภัย:**
   - ✅ อย่ารัน container ด้วย root user
   - ✅ จำกัดขนาดไฟล์ upload (ตั้งไว้ที่ 16MB)
   - ✅ ใช้ auto-cleanup เพื่อลบไฟล์เก่า
   - ✅ Validate file types ก่อน upload

4. **Performance:**
   - ✅ ใช้ named volumes บน production
   - ✅ ตั้ง cleanup interval ที่เหมาะสม
   - ✅ Monitor และจำกัด volume size

### ตัวอย่าง Deploy Script

```bash
#!/bin/bash
# deploy.sh - Production deployment script

# Pull latest code
git pull origin main

# Build new image
docker-compose build --no-cache

# Stop old container
docker-compose down

# Start new container
docker-compose up -d

# Check health
sleep 10
curl -f http://localhost:8000/ || echo "Health check failed!"

# View logs
docker-compose logs --tail=50
```

### Environment Variables

สามารถกำหนด environment variables เพิ่มเติมได้:

```yaml
# ใน docker-compose.yml
environment:
  - FLASK_ENV=production
  - PYTHONUNBUFFERED=1
  - MAX_CONTENT_LENGTH=16777216  # 16MB in bytes
  - CLEANUP_INTERVAL_HOURS=6
  - FILE_MAX_AGE_HOURS=24
```

### การ Monitor

```bash
# ดู resource usage
docker stats solar_cal_ponix-solar-analyzer-1

# ตรวจสอบ health
docker-compose ps

# ดู network
docker network inspect solar_cal_ponix_default
```

## สรุป

- **Production**: ใช้ `docker-compose.yml` (named volumes)
- **Development**: ใช้ `docker-compose.dev.yml` (bind mounts)
- **Backup**: ใช้ docker volume commands
- **Monitor**: ดู logs และ disk space เป็นประจำ
- **Security**: ใช้ non-root user และ auto-cleanup
