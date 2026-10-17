import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/broker_service.dart';
import '../models/broker.dart';
import 'broker_detail_screen.dart';

class BrokersScreen extends StatefulWidget {
  const BrokersScreen({super.key});

  @override
  State<BrokersScreen> createState() => _BrokersScreenState();
}

class _BrokersScreenState extends State<BrokersScreen> {
  List<Broker> _brokers = [];
  List<Broker> _filteredBrokers = [];
  bool _isLoading = true;
  String _searchQuery = '';
  String? _selectedCategory;
  List<String> _categories = [];

  @override
  void initState() {
    super.initState();
    _loadBrokers();
  }

  Future<void> _loadBrokers() async {
    setState(() {
      _isLoading = true;
    });

    try {
      final brokerService = context.read<BrokerService>();
      final brokers = await brokerService.getBrokers();
      final categories = await brokerService.getCategories();

      setState(() {
        _brokers = brokers;
        _filteredBrokers = brokers;
        _categories = categories;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _filterBrokers() {
    setState(() {
      _filteredBrokers = _brokers.where((broker) {
        final matchesSearch = _searchQuery.isEmpty ||
            broker.name.toLowerCase().contains(_searchQuery.toLowerCase()) ||
            broker.description
                .toLowerCase()
                .contains(_searchQuery.toLowerCase());
        final matchesCategory =
            _selectedCategory == null || broker.category == _selectedCategory;
        return matchesSearch && matchesCategory;
      }).toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          _buildSearchBar(),
          if (_categories.isNotEmpty) _buildCategoryFilter(),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _filteredBrokers.isEmpty
                    ? _buildEmptyState()
                    : _buildBrokersList(),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchBar() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: TextField(
        decoration: InputDecoration(
          hintText: 'Search data brokers...',
          prefixIcon: const Icon(Icons.search),
          suffixIcon: _searchQuery.isNotEmpty
              ? IconButton(
                  icon: const Icon(Icons.clear),
                  onPressed: () {
                    setState(() {
                      _searchQuery = '';
                    });
                    _filterBrokers();
                  },
                )
              : null,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          filled: true,
        ),
        onChanged: (value) {
          setState(() {
            _searchQuery = value;
          });
          _filterBrokers();
        },
      ),
    );
  }

  Widget _buildCategoryFilter() {
    return SizedBox(
      height: 50,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        children: [
          _buildCategoryChip('All', null),
          ..._categories.map((category) => _buildCategoryChip(category, category)),
        ],
      ),
    );
  }

  Widget _buildCategoryChip(String label, String? category) {
    final isSelected = _selectedCategory == category;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: FilterChip(
        label: Text(label),
        selected: isSelected,
        onSelected: (selected) {
          setState(() {
            _selectedCategory = selected ? category : null;
          });
          _filterBrokers();
        },
      ),
    );
  }

  Widget _buildBrokersList() {
    return RefreshIndicator(
      onRefresh: _loadBrokers,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _filteredBrokers.length,
        itemBuilder: (context, index) {
          final broker = _filteredBrokers[index];
          return _buildBrokerCard(broker);
        },
      ),
    );
  }

  Widget _buildBrokerCard(Broker broker) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => BrokerDetailScreen(broker: broker),
            ),
          );
        },
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          broker.name,
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          broker.category,
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right, color: Colors.grey[400]),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                broker.description,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: Colors.grey[700],
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _buildInfoChip(
                    broker.optOutMethod.type.replaceAll('_', ' '),
                    Icons.assignment_outlined,
                  ),
                  if (broker.estimatedResponseDays != null)
                    _buildInfoChip(
                      '~${broker.estimatedResponseDays} days',
                      Icons.schedule,
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInfoChip(String label, IconData icon) {
    return Chip(
      avatar: Icon(icon, size: 16),
      label: Text(
        label,
        style: const TextStyle(fontSize: 11),
      ),
      padding: EdgeInsets.zero,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.search_off, size: 64, color: Colors.grey[400]),
          const SizedBox(height: 16),
          Text(
            'No brokers found',
            style: TextStyle(
              fontSize: 18,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Try adjusting your search or filters',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[500],
            ),
          ),
        ],
      ),
    );
  }
}
