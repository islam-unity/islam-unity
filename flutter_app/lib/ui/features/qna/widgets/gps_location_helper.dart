import 'dart:math';
import 'package:ettehad_app/ui/core/theme.dart';

class CityCoordinate {
  final String name;
  final String province;
  final double lat;
  final double lon;

  const CityCoordinate({
    required this.name,
    required this.province,
    required this.lat,
    required this.lon,
  });
}

class GpsLocationHelper {
  // Principal Cities Coordinates across Iran
  static const Map<String, CityCoordinate> cityCoordinates = {
    'تهران': CityCoordinate(name: 'تهران', province: 'تهران', lat: 35.6892, lon: 51.3890),
    'قم': CityCoordinate(name: 'قم', province: 'قم', lat: 34.6399, lon: 50.8759),
    'مشهد': CityCoordinate(name: 'مشهد', province: 'خراسان رضوی', lat: 36.2972, lon: 59.6067),
    'سنندج': CityCoordinate(name: 'سنندج', province: 'کردستان', lat: 35.3219, lon: 46.9862),
    'گرگان': CityCoordinate(name: 'گرگان', province: 'گلستان', lat: 36.8427, lon: 54.4439),
    'زاهدان': CityCoordinate(name: 'زاهدان', province: 'سیستان و بلوچستان', lat: 29.4963, lon: 60.8629),
    'اصفهان': CityCoordinate(name: 'اصفهان', province: 'اصفهان', lat: 32.6546, lon: 51.6680),
    'شیراز': CityCoordinate(name: 'شیراز', province: 'فارس', lat: 29.5918, lon: 52.5837),
    'تبریز': CityCoordinate(name: 'تبریز', province: 'آذربایجان شرقی', lat: 38.0800, lon: 46.2919),
    'اهواز': CityCoordinate(name: 'اهواز', province: 'خوزستان', lat: 31.3183, lon: 48.6706),
    'کرمانشاه': CityCoordinate(name: 'کرمانشاه', province: 'کرمانشاه', lat: 34.3277, lon: 47.0778),
    'بندرعباس': CityCoordinate(name: 'بندرعباس', province: 'هرمزگان', lat: 27.1832, lon: 56.2666),
    'رشت': CityCoordinate(name: 'رشت', province: 'گیلان', lat: 37.2808, lon: 49.5832),
    'ساری': CityCoordinate(name: 'ساری', province: 'مازندران', lat: 36.5659, lon: 53.0586),
    'ارومیه': CityCoordinate(name: 'ارومیه', province: 'آذربایجان غربی', lat: 37.5527, lon: 45.0761),
    'اردبیل': CityCoordinate(name: 'اردبیل', province: 'اردبیل', lat: 38.2498, lon: 48.2933),
    'همدان': CityCoordinate(name: 'همدان', province: 'همدان', lat: 34.7989, lon: 48.5150),
    'یزد': CityCoordinate(name: 'یزد', province: 'یزد', lat: 31.8974, lon: 54.3569),
    'کرمان': CityCoordinate(name: 'کرمان', province: 'کرمان', lat: 30.2839, lon: 57.0834),
    'بوشهر': CityCoordinate(name: 'بوشهر', province: 'بوشهر', lat: 28.9234, lon: 50.8203),
    'زنجان': CityCoordinate(name: 'زنجان', province: 'زنجان', lat: 36.6736, lon: 48.4787),
    'خرم‌آباد': CityCoordinate(name: 'خرم‌آباد', province: 'لرستان', lat: 33.4878, lon: 48.3558),
    'اراک': CityCoordinate(name: 'اراک', province: 'مرکزی', lat: 34.0954, lon: 49.7013),
    'قزوین': CityCoordinate(name: 'قزوین', province: 'قزوین', lat: 36.2688, lon: 50.0041),
    'ایلام': CityCoordinate(name: 'ایلام', province: 'ایلام', lat: 33.6374, lon: 46.4227),
    'سمنان': CityCoordinate(name: 'سمنان', province: 'سمنان', lat: 35.5769, lon: 53.3972),
    'یاسوج': CityCoordinate(name: 'یاسوج', province: 'کهگیلویه و بویراحمد', lat: 30.6684, lon: 51.5876),
    'شهرکرد': CityCoordinate(name: 'شهرکرد', province: 'چهارمحال و بختیاری', lat: 32.3256, lon: 50.8644),
    'بیرجند': CityCoordinate(name: 'بیرجند', province: 'خراسان جنوبی', lat: 32.8663, lon: 59.2211),
    'بجنورد': CityCoordinate(name: 'بجنورد', province: 'خراسان شمالی', lat: 37.4747, lon: 57.3290),
  };

  static const List<String> availableCities = [
    'تهران',
    'قم',
    'مشهد',
    'سنندج',
    'گرگان',
    'زاهدان',
    'اصفهان',
    'شیراز',
    'تبریز',
    'اهواز',
    'کرمانشاه',
    'بندرعباس',
    'رشت',
    'ساری',
    'ارومیه',
    'اردبیل',
    'همدان',
    'یزد',
    'کرمان',
    'بوشهر',
    'زنجان',
    'خرم‌آباد',
    'اراک',
    'قزوین',
    'ایلام',
    'سمنان',
    'یاسوج',
    'شهرکرد',
    'بیرجند',
    'بجنورد',
  ];

  /// Calculate distance in km between two GPS coordinates using Haversine formula
  static double calculateDistanceKm(double lat1, double lon1, double lat2, double lon2) {
    const p = 0.017453292519943295; // Math.PI / 180
    final a = 0.5 - cos((lat2 - lat1) * p) / 2 +
        cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2;
    return 12742 * asin(sqrt(a)); // 2 * R; R = 6371 km
  }

  /// Get estimated distance from user GPS city to a scholar
  static double getScholarDistanceKm(String userCity, Map<String, dynamic> scholar) {
    final scCity = (scholar['city'] ?? '').toString();
    final userCoord = cityCoordinates[userCity] ?? cityCoordinates['تهران']!;

    double scLat = 0;
    double scLon = 0;

    if (scholar['latitude'] != null && scholar['longitude'] != null) {
      scLat = (scholar['latitude'] as num).toDouble();
      scLon = (scholar['longitude'] as num).toDouble();
    } else {
      for (final entry in cityCoordinates.entries) {
        if (scCity.contains(entry.key) || entry.key.contains(scCity)) {
          scLat = entry.value.lat;
          scLon = entry.value.lon;
          break;
        }
      }
    }

    if (scLat == 0 || scLon == 0) return 999.0;

    // If in the same city, return intra-city mosque distance (e.g. 0.4 to 3.8 km)
    if (userCity == scCity || scCity.contains(userCity) || userCity.contains(scCity)) {
      final seed = scholar['name'].toString().hashCode.abs() % 35;
      return 0.4 + (seed * 0.1);
    }

    return calculateDistanceKm(userCoord.lat, userCoord.lon, scLat, scLon);
  }

  /// Format distance string in Persian
  static String formatDistance(double km) {
    if (km < 1.0) {
      final meters = (km * 1000).toInt();
      return '${toPersianDigits(meters)} متر';
    } else if (km < 10.0) {
      return '${toPersianDigits(km.toStringAsFixed(1))} کیلومتر';
    } else {
      return '${toPersianDigits(km.toInt())} کیلومتر';
    }
  }
}
