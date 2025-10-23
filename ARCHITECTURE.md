# File Management Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Solar Analyzer Pro                          │
│                   Docker Container (app user)                   │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Flask Application (app.py)                               │ │
│  │  - Handles file uploads                                   │ │
│  │  - Generates graphs and reports                           │ │
│  │  - Auto-cleanup old files (24hrs)                         │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │         │                           │
│                           ▼         ▼                           │
│           ┌──────────────────┐  ┌──────────────────┐           │
│           │  /app/uploads    │  │ /app/static/     │           │
│           │                  │  │    outputs       │           │
│           │  - CSV files     │  │  - PNG graphs    │           │
│           │  - Temporary     │  │  - PDF reports   │           │
│           └──────────────────┘  └──────────────────┘           │
│                    │                     │                      │
└────────────────────┼─────────────────────┼──────────────────────┘
                     │                     │
                     ▼                     ▼
         ┌────────────────────┐ ┌────────────────────┐
         │  Docker Volume     │ │  Docker Volume     │
         │  solar-uploads     │ │  solar-outputs     │
         │                    │ │                    │
         │  Persistent        │ │  Persistent        │
         │  Storage           │ │  Storage           │
         └────────────────────┘ └────────────────────┘
```

## Production Mode (Named Volumes)

**docker-compose.yml**

```yaml
volumes:
  - solar-uploads:/app/uploads
  - solar-outputs:/app/static/outputs
```

**Advantages:**
- ✅ Data persists across container restarts
- ✅ Better performance on macOS/Windows
- ✅ Isolated from host filesystem (more secure)
- ✅ Easy to backup with Docker commands
- ✅ Portable across different hosts

**Data Location:**
- Linux: `/var/lib/docker/volumes/`
- macOS: Docker VM storage
- Windows: WSL2 filesystem

**Access Files:**
```bash
# View files
docker-compose exec solar-analyzer ls /app/uploads

# Copy out
docker cp container:/app/uploads/file.csv ./local-file.csv

# Backup entire volume
docker run --rm -v solar-uploads:/data -v $(pwd):/backup \
  alpine tar czf /backup/uploads.tar.gz -C /data .
```

## Development Mode (Bind Mounts)

**docker-compose.dev.yml**

```yaml
volumes:
  - ./uploads:/app/uploads
  - ./static/outputs:/app/static/outputs
```

**Advantages:**
- ✅ Direct access to files on host
- ✅ Easy to inspect/debug
- ✅ No need to copy files in/out
- ✅ Quick to clear files manually

**Data Location:**
- `./uploads/` on your host machine
- `./static/outputs/` on your host machine

**Access Files:**
```bash
# View files directly
ls -la uploads/
ls -la static/outputs/

# Edit or delete files
rm uploads/old-file.csv
```

## File Lifecycle

```
1. User Upload
   └─> CSV file saved to /app/uploads/
       └─> Filename: energy_data_YYYYMMDD_HHMMSS.csv

2. Processing
   └─> Flask app reads CSV
       └─> Generates graphs and reports
           └─> Saved to /app/static/outputs/
               ├─> solar_daily_analysis_YYYY-MM-DD.png
               ├─> solar_weekly_summary.png
               └─> solar_analysis_report_YYYYMMDD_HHMMSS.pdf

3. Auto-Cleanup (Background Thread)
   └─> Runs every 6 hours
       └─> Deletes files older than 24 hours
           ├─> From /app/uploads/
           └─> From /app/static/outputs/
```

## Directory Structure in Git

```
.
├── uploads/
│   └── .gitkeep              # Tracked in git
│   └── *.csv                 # Ignored by .gitignore
│
├── static/
│   └── outputs/
│       └── .gitkeep          # Tracked in git
│       └── *.png             # Ignored by .gitignore
│       └── *.pdf             # Ignored by .gitignore
```

**Git Configuration:**

`.gitignore`:
```gitignore
uploads/*          # Ignore all files in uploads/
!uploads/.gitkeep  # Except .gitkeep

static/outputs/*           # Ignore all files in outputs/
!static/outputs/.gitkeep   # Except .gitkeep
```

`.dockerignore`:
```dockerignore
uploads/*          # Don't include uploaded files in image
!uploads/.gitkeep  # But include .gitkeep to create directory

static/outputs/*           # Don't include output files in image
!static/outputs/.gitkeep   # But include .gitkeep to create directory
```

## Security & Permissions

```
Container User: app (non-root)
UID/GID: Created by useradd in Dockerfile

Directory Permissions:
  /app/uploads/         -> 755 (rwxr-xr-x)
  /app/static/outputs/  -> 755 (rwxr-xr-x)

Owner:
  app:app (non-root user)
```

## Backup Strategy

### Automatic Cleanup
- Runs every 6 hours
- Deletes files older than 24 hours
- Runs in background thread (daemon)

### Manual Backup (Production)
```bash
# Create dated backup
DATE=$(date +%Y%m%d)

# Backup uploads
docker run --rm \
  -v solar_cal_ponix_solar-uploads:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/uploads-$DATE.tar.gz -C /data .

# Backup outputs
docker run --rm \
  -v solar_cal_ponix_solar-outputs:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/outputs-$DATE.tar.gz -C /data .
```

### Manual Backup (Development)
```bash
# Simple copy (bind mounts)
DATE=$(date +%Y%m%d)
tar czf uploads-$DATE.tar.gz uploads/
tar czf outputs-$DATE.tar.gz static/outputs/
```

## Migration Between Modes

### From Development to Production
```bash
# 1. Stop development
docker-compose -f docker-compose.dev.yml down

# 2. Create volumes and copy data
docker volume create solar_cal_ponix_solar-uploads
docker volume create solar_cal_ponix_solar-outputs

docker run --rm \
  -v $(pwd)/uploads:/source \
  -v solar_cal_ponix_solar-uploads:/dest \
  alpine sh -c "cp -av /source/* /dest/"

docker run --rm \
  -v $(pwd)/static/outputs:/source \
  -v solar_cal_ponix_solar-outputs:/dest \
  alpine sh -c "cp -av /source/* /dest/"

# 3. Start production
docker-compose up -d
```

### From Production to Development
```bash
# 1. Stop production
docker-compose down

# 2. Copy data out
docker run --rm \
  -v solar_cal_ponix_solar-uploads:/source \
  -v $(pwd)/uploads:/dest \
  alpine sh -c "cp -av /source/* /dest/"

docker run --rm \
  -v solar_cal_ponix_solar-outputs:/source \
  -v $(pwd)/static/outputs:/dest \
  alpine sh -c "cp -av /source/* /dest/"

# 3. Start development
docker-compose -f docker-compose.dev.yml up -d
```

## Monitoring

### Disk Usage
```bash
# Check volume sizes
docker system df -v

# Check specific volume
docker run --rm \
  -v solar_cal_ponix_solar-uploads:/data \
  alpine du -sh /data
```

### File Count
```bash
# Count files in volumes
docker-compose exec solar-analyzer \
  sh -c "find /app/uploads -type f | wc -l"

docker-compose exec solar-analyzer \
  sh -c "find /app/static/outputs -type f | wc -l"
```

### Cleanup Events
```bash
# Watch cleanup logs
docker-compose logs -f | grep -i "removed"
```

## Best Practices

1. **Production**: Always use named volumes
2. **Development**: Use bind mounts for convenience
3. **Backup**: Schedule regular backups of volumes
4. **Monitoring**: Check disk usage regularly
5. **Cleanup**: Let auto-cleanup handle old files
6. **Security**: Never run container as root
7. **Testing**: Use development mode for testing
8. **Deployment**: Use production mode for production

## Troubleshooting

### Issue: Permission Denied
```bash
# Fix ownership
docker-compose exec -u root solar-analyzer \
  chown -R app:app /app/uploads /app/static/outputs

# Fix permissions
docker-compose exec -u root solar-analyzer \
  chmod -R 755 /app/uploads /app/static/outputs
```

### Issue: Disk Full
```bash
# Clean up old files manually
docker-compose exec solar-analyzer \
  find /app/uploads -type f -mtime +1 -delete

docker-compose exec solar-analyzer \
  find /app/static/outputs -type f -mtime +1 -delete
```

### Issue: Lost Data
```bash
# Check if volume exists
docker volume ls | grep solar

# Restore from backup
docker run --rm \
  -v solar_cal_ponix_solar-uploads:/data \
  -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/uploads-backup.tar.gz"
```
