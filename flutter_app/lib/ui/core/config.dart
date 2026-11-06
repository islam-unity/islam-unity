class EttehadConfig {
  /// Base API URL for Ettehad system
  static const String productionApiBase = 'https://api.unitysi.ir';

  /// Primary list of API hosts (Production domain first, followed by local fallback for dev)
  static const List<String> apiHosts = [
    productionApiBase,
    'http://10.0.2.2:8000',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
  ];
}
