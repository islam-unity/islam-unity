from sqlalchemy import Column, String, Boolean, DateTime, func, Index
from app.db.base import Base

class CityPrayerTime(Base):
    __tablename__ = "city_prayer_times"
    __table_args__ = (
        Index("ix_prayer_times_city_active", "city_name", "is_active"),
    )

    city_id = Column(String(64), primary_key=True, index=True) # e.g. "tehran", "mashhad", "isfahan"
    city_name = Column(String(128), nullable=False, index=True) # e.g. "تهران (پایتخت)", "مشهد مقدس"
    province = Column(String(128), nullable=True) # e.g. "تهران", "خراسان رضوی"
    country = Column(String(64), default="IR")

    # Prayer times in HH:MM format
    fajr = Column(String(16), nullable=False)     # اذان صبح
    sunrise = Column(String(16), nullable=False)  # طلوع آفتاب
    dhuhr = Column(String(16), nullable=False)    # اذان ظهر
    asr = Column(String(16), nullable=False)      # اذان عصر
    sunset = Column(String(16), nullable=False)   # غروب آفتاب
    maghrib = Column(String(16), nullable=False)  # اذان مغرب
    isha = Column(String(16), nullable=False)     # اذان عشاء
    midnight = Column(String(16), nullable=False) # نیمه‌شب شرعی

    calculation_method = Column(String(128), default="مؤسسه ژئوفیزیک دانشگاه تهران")
    source = Column(String(64), default="admin_json") # admin_json, geophysics, aladhan
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def to_dict(self):
        return {
            "city_id": self.city_id,
            "city_name": self.city_name,
            "province": self.province or "",
            "country": self.country or "IR",
            "times": {
                "fajr": self.fajr,
                "sunrise": self.sunrise,
                "dhuhr": self.dhuhr,
                "asr": self.asr,
                "sunset": self.sunset,
                "maghrib": self.maghrib,
                "isha": self.isha,
                "midnight": self.midnight
            },
            "calculation_method": self.calculation_method,
            "source": self.source,
            "is_active": self.is_active,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
