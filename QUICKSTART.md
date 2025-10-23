# คู่มือเริ่มต้นใช้งานระบบ Docker (Quick Start Guide)

## สำหรับผู้ใช้งานทั่วไป (For End Users)

### วิธีที่ 1: Deploy แบบง่าย (Recommended)

```bash
# 1. ดาวน์โหลดโค้ด
git clone https://github.com/nuttooo/solar_cal_ponix.git
cd solar_cal_ponix

# 2. รันคำสั่งเดียว - สำหรับ Production
./deploy.sh production

# 3. เปิดเว็บเบราว์เซอร์ไปที่
http://localhost:8000
```

### วิธีที่ 2: Deploy แบบ Manual

```bash
# 1. ดาวน์โหลดโค้ด
git clone https://github.com/nuttooo/solar_cal_ponix.git
cd solar_cal_ponix

# 2. Build และรัน
docker-compose up -d

# 3. ตรวจสอบสถานะ
docker-compose ps

# 4. เปิดเว็บเบราว์เซอร์ไปที่
http://localhost:8000
```

## สำหรับผู้พัฒนา (For Developers)

### Development Mode

```bash
# 1. Clone repository
git clone https://github.com/nuttooo/solar_cal_ponix.git
cd solar_cal_ponix

# 2. รัน development mode (bind mounts)
./deploy.sh dev

# 3. ไฟล์ที่อัปโหลดและ output จะอยู่ที่:
# - uploads/
# - static/outputs/

# 4. ดู logs แบบ real-time
docker-compose -f docker-compose.dev.yml logs -f
```

## คำสั่งที่ใช้บ่อย (Common Commands)

### ดูสถานะ (Check Status)
```bash
docker-compose ps
```

### ดู Logs
```bash
# ดู logs ทั้งหมด
docker-compose logs

# ดูแบบ real-time
docker-compose logs -f

# ดูเฉพาะ 50 บรรทัดล่าสุด
docker-compose logs --tail=50
```

### หยุดและเริ่มใหม่ (Stop and Restart)
```bash
# หยุด
docker-compose down

# เริ่มใหม่
docker-compose up -d

# Restart (ไม่ลบ container)
docker-compose restart
```

### อัพเดตโค้ด (Update Code)
```bash
# 1. Pull โค้ดใหม่
git pull

# 2. Build image ใหม่
docker-compose build

# 3. Restart
docker-compose down
docker-compose up -d
```

### ลบข้อมูลทั้งหมด (Clean Everything)
```bash
# ลบ containers และ volumes (ข้อมูลจะหายทั้งหมด!)
docker-compose down -v
```

## การจัดการไฟล์ (File Management)

### ดูไฟล์ที่อัปโหลด (View Uploaded Files)

#### Production Mode (Named Volumes):
```bash
# เข้าไปดูใน container
docker-compose exec solar-analyzer ls -la /app/uploads

# หรือ copy ออกมาดู
docker cp solar_cal_ponix-solar-analyzer-1:/app/uploads ./temp-uploads
```

#### Development Mode (Bind Mounts):
```bash
# ดูได้เลยบน host
ls -la uploads/
```

### ลบไฟล์เก่า (Clean Old Files)
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

### Backup ข้อมูล (Backup Data)
```bash
# Backup uploads
docker run --rm -v solar_cal_ponix_solar-uploads:/data -v $(pwd):/backup \
  alpine tar czf /backup/uploads-backup-$(date +%Y%m%d).tar.gz -C /data .

# Backup outputs
docker run --rm -v solar_cal_ponix_solar-outputs:/data -v $(pwd):/backup \
  alpine tar czf /backup/outputs-backup-$(date +%Y%m%d).tar.gz -C /data .
```

### Restore ข้อมูล (Restore Data)
```bash
# Restore uploads
docker run --rm -v solar_cal_ponix_solar-uploads:/data -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/uploads-backup-YYYYMMDD.tar.gz"

# Restore outputs
docker run --rm -v solar_cal_ponix_solar-outputs:/data -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/outputs-backup-YYYYMMDD.tar.gz"
```

## การแก้ปัญหา (Troubleshooting)

### ปัญหา: Port 8000 ถูกใช้งานอยู่
```bash
# หา process ที่ใช้ port 8000
sudo lsof -i :8000

# หรือเปลี่ยน port ใน docker-compose.yml
# เปลี่ยนจาก "8000:8000" เป็น "8080:8000"
```

### ปัญหา: Permission Denied
```bash
# แก้ไข permission ใน container
docker-compose exec -u root solar-analyzer chown -R app:app /app/uploads
docker-compose exec -u root solar-analyzer chown -R app:app /app/static/outputs
```

### ปัญหา: Container ไม่ขึ้น (Container Won't Start)
```bash
# 1. ดู logs เพื่อหาสาเหตุ
docker-compose logs

# 2. ลบทุกอย่างและเริ่มใหม่
docker-compose down -v
docker-compose up -d

# 3. Build ใหม่ไม่ใช้ cache
docker-compose build --no-cache
docker-compose up -d
```

### ปัญหา: หน่วยความจำเต็ม (Disk Full)
```bash
# ตรวจสอบพื้นที่
docker system df -v

# ลบ images และ containers ที่ไม่ใช้
docker system prune -a

# ลบ volumes ที่ไม่ใช้ (ระวัง! ข้อมูลจะหาย)
docker volume prune
```

## เอกสารเพิ่มเติม (Additional Documentation)

- **คู่มือ Docker ฉบับเต็ม**: [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)
- **คู่มือการใช้งาน**: [README.md](README.md)
- **สรุปผลการทดสอบ**: [TEST_SUMMARY.md](TEST_SUMMARY.md)

## ติดต่อและสนับสนุน (Support)

หากพบปัญหาหรือต้องการความช่วยเหลือ:
1. ตรวจสอบ logs: `docker-compose logs`
2. อ่านคู่มือ DOCKER_DEPLOYMENT.md
3. เปิด Issue ใน GitHub

---

**หมายเหตุ**: 
- ระบบจะลบไฟล์เก่ากว่า 24 ชั่วโมงอัตโนมัติทุก 6 ชั่วโมง
- แนะนำให้ backup ข้อมูลสำคัญเป็นประจำ
- สำหรับ production ควรใช้ named volumes (docker-compose.yml)
- สำหรับ development ใช้ bind mounts (docker-compose.dev.yml)
