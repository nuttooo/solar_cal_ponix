# Solar Analyzer Pro - Web Application

เว็บแอปพลิเคชันสำหรับวิเคราะห์ระบบโซลาร์เซลล์และแบตเตอรี่แบบออนไลน์

## ฟีเจอร์หลัก

- 📁 อัปโหลดไฟล์ข้อมูลการใช้ไฟฟ้า (CSV)
- ⚙️ ตั้งค่าพารามิเตอร์ระบบโซลาร์และแบตเตอรี่
- 📊 สร้างกราฟการวิเคราะห์รายวันและรายสัปดาห์
- 📄 ส่งออกรายงาน PDF พร้อมกราฟและข้อมูลทั้งหมด
- 📥 ดาวน์โหลดกราฟและรายงานได้ทันที

## การติดตั้ง

> 📘 **Quick Start**: อ่าน [QUICKSTART.md](QUICKSTART.md) สำหรับคำแนะนำเริ่มต้นอย่างรวดเร็ว

### วิธีที่ 1: ติดตั้งด้วย Docker (แนะนำ)

#### Production Deployment
```bash
# Build และรัน
docker-compose up -d

# ตรวจสอบสถานะ
docker-compose ps

# ดู logs
docker-compose logs -f
```

#### Development Deployment
```bash
# ใช้สำหรับการพัฒนา (bind mounts)
docker-compose -f docker-compose.dev.yml up -d
```

**อ่านเพิ่มเติม:** ดู [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) สำหรับคู่มือการ deploy แบบละเอียด

### วิธีที่ 2: ติดตั้งแบบ Manual

### 1. ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

### 2. เรียกใช้งานแอปพลิเคชัน

```bash
python app.py
```

### 3. เปิดเว็บบราวเซอร์

ไปที่ http://localhost:5000

## รูปแบบไฟล์ข้อมูล

ไฟล์ CSV ที่อัปโหลดต้องมีคอลัมน์ต่อไปนี้:

- `datetime`: วันที่และเวลา (รูปแบบ: d/m/Y H.M)
- `rate_a`: อัตราการใช้ไฟฟ้า rate_a (kW)
- `rate_b`: อัตราการใช้ไฟฟ้า rate_b (kW) 
- `rate_c`: อัตราการใช้ไฟฟ้า rate_c (kW)

**ตัวอย่างข้อมูล:**
```
datetime,rate_a,empty1,rate_b,empty2,rate_c,empty3
01/01/2024 0.00,1.2,,0.8,,0.5,
01/01/2024 0.15,1.1,,0.7,,0.4,
...
```

## การใช้งาน

### 1. อัปโหลดไฟล์

1. คลิกที่พื้นที่อัปโหลดหรือลากไฟล์ CSV มาวาง
2. รอการตรวจสอบไฟล์
3. คลิก "อัปโหลดไฟล์"

### 2. ตั้งค่าพารามิเตอร์

- **ขนาดระบบโซลาร์ (MWp)**: กำลังการผลิตสูงสุดของระบบโซลาร์
- **ชั่วโมงแดดเฉลี่ย**: จำนวนชั่วโมงที่แดดแรงเฉลี่ยต่อวัน
- **เกณฑ์เริ่มจ่ายแบต (W)**: เมื่อโหลดเกินค่านี้จะเริ่มใช้จากแบตเตอรี่
- **ขนาดแบตเตอรี่ (kWh)**: ใส่ 0 เพื่อให้คำนวณขนาดที่เหมาะสมอัตโนมัติ

### 3. ดูผลลัพธ์

- สรุปข้อมูลการวิเคราะห์
- กราฟการวิเคราะห์รายวันและรายสัปดาห์
- ตารางข้อมูลรายวัน
- ดาวน์โหลดกราฟและรายงาน PDF

## โครงสร้างไฟล์

```
.
├── app.py                 # Flask web application
├── solar_analyzer_pro.py  # Core analysis logic
├── requirements.txt       # Python dependencies
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── index.html        # Home page (file upload)
│   ├── configure.html    # Configuration page
│   └── results.html      # Results page
├── static/               # Static files
│   ├── css/
│   ├── js/
│   └── outputs/          # Generated graphs and PDFs
├── uploads/              # Uploaded CSV files
└── data/                 # Sample data files
```

## เทมเพลตที่ตั้งไว้ล่วงหน้า

มีเทมเพลตสำหรับการตั้งค่าที่ตั้งไว้ล่วงหน้า:

- **🏠 ที่พักอาศัย**: โซลาร์ 3-5 MWp, แบต 10-20 kWh
- **🏢 สำนักงาน/ร้านค้า**: โซลาร์ 5-10 MWp, แบต 20-50 kWh  
- **🏭 โรงงาน**: โซลาร์ 10-50 MWp, แบต 50-200 kWh

## การปรับแต่ง

สามารถปรับแต่งส่วนต่างๆ ของแอปพลิเคชันได้:

- แก้ไขพารามิเตอร์การวิเคราะห์ใน `solar_analyzer_pro.py`
- ปรับแต่ง UI ในไฟล์ HTML templates
- เปลี่ยนรูปแบบกราฟในส่วนของ matplotlib

## ข้อจำกัด

- รองรับไฟล์ CSV เท่านั้น
- ขนาดไฟล์สูงสุด 16MB
- ต้องมีข้อมูลครบถ้วนตามรูปแบบที่กำหนด

## ปัญหาที่อาจพบ

### ติดตั้งฟอนต์ภาษาไทย
หากกราฟแสดงภาษาไทยไม่ถูกต้อง ให้ติดตั้งฟอนต์เพิ่มเติม:

```bash
# บน Ubuntu/Debian
sudo apt-get install fonts-thai-tlwg

# บน macOS
brew install font-thana-lakkhana

# บน Windows
ฟอนต์ Tahoma มีมาให้ตามปกติ
```

### ข้อผิดพลาด ModuleNotFoundError
ติดตั้ง dependencies ทั้งหมดตาม requirements.txt:

```bash
pip install -r requirements.txt
```

## ผู้พัฒนา

Solar Analyzer Pro - เครื่องมือวิเคราะห์ระบบโซลาร์เซลล์และแบตเตอรี่