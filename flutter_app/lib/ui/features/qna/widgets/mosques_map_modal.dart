import 'package:flutter/material.dart';
import '../../../../data/ettehad_repository.dart';
import '../../../../ui/core/theme.dart';

class MosquesMapModal extends StatefulWidget {
  final EttehadRepository? repo;

  const MosquesMapModal({super.key, this.repo});

  static void show(BuildContext context, {EttehadRepository? repo}) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => MosquesMapModal(repo: repo),
    );
  }

  @override
  State<MosquesMapModal> createState() => _MosquesMapModalState();
}

class _MosquesMapModalState extends State<MosquesMapModal> {
  String _selectedFilter = 'all';
  bool _isLoading = true;
  String? _errorMessage;
  List<Map<String, dynamic>> _mosques = [];

  @override
  void initState() {
    super.initState();
    _loadMosques();
  }

  Future<void> _loadMosques() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      if (widget.repo != null) {
        final list = await widget.repo!.fetchNearbyMosquesAndScholars();
        if (mounted) {
          setState(() {
            _mosques = list;
            _isLoading = false;
          });
        }
      } else {
        setState(() {
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage = 'خطا در دریافت نشانی مساجد از سرور.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _selectedFilter == 'all'
        ? _mosques
        : _mosques.where((m) => (m['type'] ?? '') == _selectedFilter).toList();

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Container(
        height: MediaQuery.of(context).size.height * 0.88,
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          children: [
            // Handle bar
            Container(
              margin: const EdgeInsets.only(top: 10, bottom: 6),
              width: 44,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            // Header
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(9),
                    decoration: BoxDecoration(
                      color: EttehadColors.emerald.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.mosque_rounded, color: EttehadColors.emeraldDark, size: 24),
                  ),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'نشانی مساجد و مراکز معارفی (GPS)',
                          style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: EttehadColors.navy),
                        ),
                        Text(
                          'مشاهده موقعیت مکانی، ساعات نماز جماعت و میز پاسخ‌گویی شرعی',
                          style: TextStyle(fontSize: 10.5, color: Colors.black54),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close_rounded, size: 22),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),

            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // Visual Map Strip Banner
                  Container(
                    height: 130,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(18),
                      gradient: const LinearGradient(
                        colors: [Color(0xFF0F5257), Color(0xFF1B6A70), Color(0xFF2E8B90)],
                        begin: Alignment.topRight,
                        end: Alignment.bottomLeft,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF0F5257).withValues(alpha: 0.2),
                          blurRadius: 10,
                          offset: const Offset(0, 3),
                        ),
                      ],
                    ),
                    child: Stack(
                      children: [
                        // Background stylized map pins pattern
                        Positioned.fill(
                          child: Opacity(
                            opacity: 0.1,
                            child: Image.asset(
                              'assets/images/app_icon.png',
                              fit: BoxFit.cover,
                            ),
                          ),
                        ),
                        Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Container(
                                margin: const EdgeInsets.symmetric(horizontal: 16),
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                decoration: BoxDecoration(
                                  color: Colors.white.withValues(alpha: 0.95),
                                  borderRadius: BorderRadius.circular(22),
                                  boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 8)],
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(Icons.my_location_rounded, color: EttehadColors.primary, size: 16),
                                    const SizedBox(width: 6),
                                    Flexible(
                                      child: Text(
                                        'موقعیت شما: تهران • ${toPersianDigits(_mosques.length)} مرکز فعال',
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: EttehadColors.ink),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 8),
                              const Text(
                                'مساجد دارای میز پاسخ‌گویی حضوری با برچسب سبز مشخص شده‌اند',
                                style: TextStyle(color: Color(0xFFE2F4F5), fontSize: 10.5),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),

                  // Filter Chips
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        _buildFilterChip('all', 'همه مساجد و مراکز'),
                        const SizedBox(width: 8),
                        _buildFilterChip('fatwa', 'دفتر پاسخگویی شرعی'),
                        const SizedBox(width: 8),
                        _buildFilterChip('unity', 'مراکز تقریب و فقه مقارن'),
                        const SizedBox(width: 8),
                        _buildFilterChip('tafsir', 'کرسی تفسیر قرآن'),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),

                  // Mosques List
                  if (_isLoading)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 40),
                      child: Center(
                        child: Column(
                          children: [
                            CircularProgressIndicator(strokeWidth: 2.5, color: EttehadColors.primary),
                            SizedBox(height: 12),
                            Text('در حال دریافت اطلاعات مراکز و مساجد نزدیک...', style: TextStyle(fontSize: 12, color: Colors.black54)),
                          ],
                        ),
                      ),
                    )
                  else if (_errorMessage != null)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 30),
                      child: Center(
                        child: Column(
                          children: [
                            const Icon(Icons.error_outline_rounded, color: Colors.redAccent, size: 36),
                            const SizedBox(height: 8),
                            Text(_errorMessage!, style: const TextStyle(fontSize: 12, color: Colors.black87)),
                            const SizedBox(height: 10),
                            OutlinedButton.icon(
                              onPressed: _loadMosques,
                              icon: const Icon(Icons.refresh_rounded, size: 16),
                              label: const Text('تلاش مجدد'),
                            ),
                          ],
                        ),
                      ),
                    )
                  else if (filtered.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 40),
                      child: Center(
                        child: Text('مرکزی با این فیلتر در نزدیکی شما یافت نشد.', style: TextStyle(fontSize: 12, color: Colors.black54)),
                      ),
                    )
                  else
                    ...filtered.map((m) => _buildMosqueCard(context, m)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilterChip(String key, String label) {
    final isSelected = _selectedFilter == key;
    return InkWell(
      onTap: () => setState(() => _selectedFilter = key),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? EttehadColors.primary : EttehadColors.surfaceLow,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? EttehadColors.primary : EttehadColors.border,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            color: isSelected ? Colors.white : EttehadColors.ink,
          ),
        ),
      ),
    );
  }

  Widget _buildMosqueCard(BuildContext context, Map<String, dynamic> m) {
    final isOpen = m['is_open'] == true;
    final features = List<String>.from(m['features'] ?? []);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: EttehadColors.border),
        boxShadow: const [
          BoxShadow(
            color: Color(0x080A2E6E),
            blurRadius: 10,
            offset: Offset(0, 3),
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: EttehadColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.location_on_rounded, color: EttehadColors.primary, size: 24),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      m['name'],
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: EttehadColors.navy),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '📍 ${m['address']}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 10.5, color: Colors.black54),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: isOpen ? const Color(0xFFD1FAE5) : const Color(0xFFEFF6FF),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: isOpen ? const Color(0xFFA7F3D0) : const Color(0xFFBFDBFE)),
                ),
                child: Text(
                  isOpen ? 'دایر • ${toPersianDigits(m['distance'])}' : toPersianDigits(m['distance']),
                  style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: isOpen ? EttehadColors.emeraldDark : EttehadColors.primary),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),

          // Prayer times info strip
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
            decoration: BoxDecoration(
              color: EttehadColors.surfaceLow,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              children: [
                const Icon(Icons.access_time_rounded, size: 14, color: EttehadColors.amberDark),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    toPersianDigits(m['prayers']),
                    style: const TextStyle(fontSize: 10.5, color: EttehadColors.ink),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),

          // Scholar presence
          Row(
            children: [
              const Icon(Icons.person_rounded, size: 14, color: EttehadColors.primary),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  'استاد حاضر: ${m['scholar']}',
                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: EttehadColors.primary),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // Feature tags
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: features.map((f) {
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: EttehadColors.emerald.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  f,
                  style: const TextStyle(fontSize: 9.5, color: EttehadColors.emeraldDark, fontWeight: FontWeight.bold),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 12),

          // Action row
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('مسیریابی به مقصد «${m['name']}» آغاز شد.'),
                        backgroundColor: EttehadColors.primary,
                      ),
                    );
                  },
                  icon: const Icon(Icons.directions_rounded, size: 16),
                  label: const Text('مسیریابی روی نقشه', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: EttehadColors.primary,
                    side: const BorderSide(color: EttehadColors.primary),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('تماس با دفتر ${m['name']} برقرار شد.'),
                      backgroundColor: EttehadColors.emerald,
                    ),
                  );
                },
                icon: const Icon(Icons.call_rounded, size: 16),
                label: const Text('تماس با دفتر', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: EttehadColors.navy,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
