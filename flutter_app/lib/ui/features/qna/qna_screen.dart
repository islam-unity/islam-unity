import 'package:flutter/material.dart';
import '../../../data/ettehad_repository.dart';
import '../../core/theme.dart';
import '../profile/profile_sheet.dart';
import 'widgets/inquiry_tracker_hero.dart';
import 'widgets/mosques_map_modal.dart';
import 'widgets/my_inquiries_tab.dart';
import 'widgets/new_inquiry_modal.dart';
import 'widgets/public_faq_tab.dart';
import 'widgets/scholar_insights_tab.dart';
import 'widgets/scholars_directory_tab.dart';
export 'widgets/scholar_chat_screen.dart';

class QnaScreen extends StatefulWidget {
  final EttehadRepository repo;

  const QnaScreen({super.key, required this.repo});

  @override
  State<QnaScreen> createState() => _QnaScreenState();
}

class _QnaScreenState extends State<QnaScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _openNewInquiryModal() {
    NewInquiryModal.show(
      context,
      widget.repo,
      onInquiryCreated: () {
        // Switch to 'My Inquiries' tab on creation
        _tabController.animateTo(0);
        setState(() {});
      },
    );
  }

  void _openMosquesMap() {
    MosquesMapModal.show(context, repo: widget.repo);
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.repo,
      builder: (context, _) {
        final chatsCount = widget.repo.scholarChats.length;

        return Scaffold(
          backgroundColor: EttehadColors.paper,
          body: NestedScrollView(
            headerSliverBuilder: (ctx, innerBoxIsScrolled) {
              return [
                // 1. Top App Bar - Clean, symmetrical, and perfectly aligned card
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 6),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(color: EttehadColors.border),
                        boxShadow: [
                          BoxShadow(
                            color: EttehadColors.navy.withValues(alpha: 0.05),
                            blurRadius: 10,
                            offset: const Offset(0, 3),
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: [
                          // Title & Branding (Right side in RTL)
                          Expanded(
                            child: Row(
                              children: [
                                Container(
                                  width: 40,
                                  height: 40,
                                  decoration: BoxDecoration(
                                    color: EttehadColors.primary,
                                    borderRadius: BorderRadius.circular(13),
                                    boxShadow: [
                                      BoxShadow(
                                        color: EttehadColors.primary.withValues(alpha: 0.25),
                                        blurRadius: 6,
                                        offset: const Offset(0, 2),
                                      ),
                                    ],
                                  ),
                                  child: const Icon(Icons.account_balance_rounded, color: Colors.white, size: 21),
                                ),
                                const SizedBox(width: 10),
                                const Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Text(
                                        'اتحادکده',
                                        style: TextStyle(
                                          fontWeight: FontWeight.w900,
                                          fontSize: 15.5,
                                          color: EttehadColors.navy,
                                        ),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      SizedBox(height: 1),
                                      Text(
                                        'میز استفتائات، فقه مقارن و مطالب اساتید',
                                        style: TextStyle(fontSize: 10.5, color: EttehadColors.inkLight),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 8),

                          // Symmetrical, aligned action buttons (Left side in RTL)
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.center,
                            children: [
                              // Mosques map button
                              InkWell(
                                onTap: _openMosquesMap,
                                borderRadius: BorderRadius.circular(12),
                                child: Container(
                                  height: 36,
                                  padding: const EdgeInsets.symmetric(horizontal: 10),
                                  decoration: BoxDecoration(
                                    color: EttehadColors.surfaceLow,
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(color: EttehadColors.border),
                                  ),
                                  child: const Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.mosque_rounded, size: 16, color: EttehadColors.primary),
                                      SizedBox(width: 5),
                                      Text(
                                        'مساجد',
                                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: EttehadColors.navy),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                              const SizedBox(width: 6),

                              // User Profile button
                              InkWell(
                                onTap: () => showEttehadUserProfile(context, widget.repo),
                                borderRadius: BorderRadius.circular(12),
                                child: Container(
                                  width: 36,
                                  height: 36,
                                  decoration: BoxDecoration(
                                    color: EttehadColors.surfaceLow,
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(color: EttehadColors.border),
                                  ),
                                  child: const Icon(Icons.person_rounded, size: 20, color: EttehadColors.primary),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ),

                // 2. Hero Tracking & Action Banner
                SliverToBoxAdapter(
                  child: InquiryTrackerHero(
                    repo: widget.repo,
                    onNewInquiryRequested: _openNewInquiryModal,
                  ),
                ),

                // 3. Persistent 4-Tab Navigation Bar
                SliverPersistentHeader(
                  pinned: true,
                  delegate: _SliverTabBarDelegate(
                    TabBar(
                      controller: _tabController,
                      isScrollable: true,
                      tabAlignment: TabAlignment.start,
                      labelColor: EttehadColors.primary,
                      unselectedLabelColor: Colors.black54,
                      indicatorColor: EttehadColors.primary,
                      indicatorWeight: 3,
                      labelStyle: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5),
                      unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.normal, fontSize: 12),
                      tabs: [
                        Tab(
                          child: Row(
                            children: [
                              const Icon(Icons.inbox_rounded, size: 16),
                              const SizedBox(width: 6),
                              const Text('استفتائات من'),
                              if (chatsCount > 0) ...[
                                const SizedBox(width: 6),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                                  decoration: BoxDecoration(
                                    color: EttehadColors.primary,
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Text(
                                    toPersianDigits(chatsCount),
                                    style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.bold),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                        const Tab(
                          child: Row(
                            children: [
                              Icon(Icons.auto_stories_rounded, size: 16),
                              SizedBox(width: 6),
                              Text('مطالب اساتید'),
                            ],
                          ),
                        ),
                        const Tab(
                          child: Row(
                            children: [
                              Icon(Icons.manage_search_rounded, size: 16),
                              SizedBox(width: 6),
                              Text('بانک پاسخ‌ها'),
                            ],
                          ),
                        ),
                        const Tab(
                          child: Row(
                            children: [
                              Icon(Icons.groups_rounded, size: 16),
                              SizedBox(width: 6),
                              Text('معرفی اساتید'),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ];
            },
            body: TabBarView(
              controller: _tabController,
              children: [
                // Tab 1: My Inquiries
                MyInquiriesTab(
                  repo: widget.repo,
                  onNewInquiryRequested: _openNewInquiryModal,
                ),

                // Tab 2: Scholar Insights & Posts (Requirement 1)
                ScholarInsightsTab(repo: widget.repo),

                // Tab 3: Public FAQ & Fatwa Bank
                PublicFaqTab(repo: widget.repo),

                // Tab 4: Scholars Directory
                ScholarsDirectoryTab(repo: widget.repo),
              ],
            ),
          ),
          floatingActionButton: chatsCount == 0
              ? null
              : Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: FloatingActionButton.extended(
                    onPressed: _openNewInquiryModal,
                    backgroundColor: EttehadColors.amberDark,
                    foregroundColor: Colors.white,
                    elevation: 4,
                    icon: const Icon(Icons.edit_note_rounded, size: 22),
                    label: const Text('طرح سوال و استفتاء جدید', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                  ),
                ),
        );
      },
    );
  }
}

class _SliverTabBarDelegate extends SliverPersistentHeaderDelegate {
  final TabBar _tabBar;

  _SliverTabBarDelegate(this._tabBar);

  @override
  double get minExtent => _tabBar.preferredSize.height;
  @override
  double get maxExtent => _tabBar.preferredSize.height;

  @override
  Widget build(BuildContext context, double shrinkOffset, bool overlapsContent) {
    return Container(
      decoration: const BoxDecoration(
        color: EttehadColors.paper,
        border: Border(bottom: BorderSide(color: EttehadColors.border, width: 1)),
      ),
      child: _tabBar,
    );
  }

  @override
  bool shouldRebuild(_SliverTabBarDelegate oldDelegate) {
    return false;
  }
}
