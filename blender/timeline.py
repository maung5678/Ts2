"""เวลาของเหตุการณ์ในคลิป 15 วิ (ใช้ร่วมกันระหว่าง scene.py กับ compose.py ให้ภาพ เสียง ซับตรงกัน)"""
G = 9.81
STONE_R = 0.17
DURATION = 15.0
DROP_T = 0.55                                     # ปล่อยลูกหิน
IMPACT_T = DROP_T + (2 * (1.0 - STONE_R) / G) ** 0.5
CUT = 4.0                                         # ตัดจากช็อตใกล้ → มุมกว้าง
PUMP_START, PUMP_END, PUMP_HZ = 4.2, 5.9, 1.6     # เพื่อนสูบลม ลูกบาสค่อย ๆ พองขึ้น
DRIBBLE_HZ = 2.2
DRIB_START = 6.1
DRIB_END = DRIB_START + 5 / DRIBBLE_HZ            # จบตอนลูกอยู่บนสุด
GATHER_END = DRIB_END + 0.35                      # รวบลูกเข้าอก แล้วหันหาที่โยน
SHOOT_T = 10.75                                   # "Into a basket"
LAND_T = SHOOT_T + 0.75
CELEB_T = 12.4                                    # ฉลอง "that's how basketball was invented"
