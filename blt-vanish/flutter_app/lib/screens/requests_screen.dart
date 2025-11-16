import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../services/storage_service.dart';
import '../models/opt_out_request.dart';

class RequestsScreen extends StatefulWidget {
  const RequestsScreen({super.key});

  @override
  State<RequestsScreen> createState() => _RequestsScreenState();
}

class _RequestsScreenState extends State<RequestsScreen> {
  List<OptOutRequest> _requests = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadRequests();
  }

  Future<void> _loadRequests() async {
    setState(() {
      _isLoading = true;
    });

    try {
      final storageService = context.read<StorageService>();
      final requests = await storageService.getRequests();

      setState(() {
        _requests = requests;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_requests.isEmpty) {
      return _buildEmptyState();
    }

    return RefreshIndicator(
      onRefresh: _loadRequests,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _requests.length,
        itemBuilder: (context, index) {
          final request = _requests[index];
          return _buildRequestCard(request);
        },
      ),
    );
  }

  Widget _buildRequestCard(OptOutRequest request) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => _showRequestDetails(request),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      request.brokerName,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  _buildStatusChip(request.status),
                ],
              ),
              const SizedBox(height: 12),
              _buildInfoRow(
                'Created',
                DateFormat.yMMMd().format(request.createdAt),
                Icons.calendar_today,
              ),
              if (request.submittedAt != null) ...[
                const SizedBox(height: 8),
                _buildInfoRow(
                  'Submitted',
                  DateFormat.yMMMd().format(request.submittedAt!),
                  Icons.send,
                ),
              ],
              if (request.completedAt != null) ...[
                const SizedBox(height: 8),
                _buildInfoRow(
                  'Completed',
                  DateFormat.yMMMd().format(request.completedAt!),
                  Icons.check_circle,
                ),
              ],
              if (request.confirmationNumber != null) ...[
                const SizedBox(height: 8),
                _buildInfoRow(
                  'Confirmation',
                  request.confirmationNumber!,
                  Icons.confirmation_number,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatusChip(RequestStatus status) {
    Color color;
    String label;

    switch (status) {
      case RequestStatus.draft:
        color = Colors.grey;
        label = 'Draft';
        break;
      case RequestStatus.pending:
        color = Colors.orange;
        label = 'Pending';
        break;
      case RequestStatus.submitted:
        color = Colors.blue;
        label = 'Submitted';
        break;
      case RequestStatus.acknowledged:
        color = Colors.lightBlue;
        label = 'Acknowledged';
        break;
      case RequestStatus.completed:
        color = Colors.green;
        label = 'Completed';
        break;
      case RequestStatus.failed:
        color = Colors.red;
        label = 'Failed';
        break;
      case RequestStatus.requiresAction:
        color = Colors.deepOrange;
        label = 'Requires Action';
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color.shade900,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 16, color: Colors.grey[600]),
        const SizedBox(width: 8),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
        const SizedBox(width: 8),
        Text(
          value,
          style: const TextStyle(fontSize: 12),
        ),
      ],
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.assignment_outlined, size: 64, color: Colors.grey[400]),
          const SizedBox(height: 16),
          Text(
            'No opt-out requests yet',
            style: TextStyle(
              fontSize: 18,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Start by searching for data brokers',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[500],
            ),
          ),
        ],
      ),
    );
  }

  void _showRequestDetails(OptOutRequest request) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.7,
        minChildSize: 0.5,
        maxChildSize: 0.95,
        expand: false,
        builder: (context, scrollController) => ListView(
          controller: scrollController,
          padding: const EdgeInsets.all(24),
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              request.brokerName,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            _buildStatusChip(request.status),
            const SizedBox(height: 24),
            Text(
              'Timeline',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            if (request.actions.isNotEmpty)
              ...request.actions.map((action) => _buildActionItem(action))
            else
              Text(
                'No actions recorded yet',
                style: TextStyle(color: Colors.grey[600]),
              ),
            if (request.notes != null && request.notes!.isNotEmpty) ...[
              const SizedBox(height: 24),
              Text(
                'Notes',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Text(request.notes!),
            ],
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () {
                      Navigator.pop(context);
                      _showDeleteConfirmation(request);
                    },
                    child: const Text('Delete'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton(
                    onPressed: () {
                      Navigator.pop(context);
                      // TODO: Update request status
                    },
                    child: const Text('Update Status'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionItem(RequestAction action) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primaryContainer,
              shape: BoxShape.circle,
            ),
            child: Icon(
              _getActionIcon(action.type),
              size: 20,
              color: Theme.of(context).colorScheme.onPrimaryContainer,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  action.description,
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text(
                  DateFormat.yMMMd().add_jm().format(action.timestamp),
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey[600],
                  ),
                ),
                if (action.details != null && action.details!.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    action.details!,
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey[700],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  IconData _getActionIcon(ActionType type) {
    switch (type) {
      case ActionType.created:
        return Icons.add_circle;
      case ActionType.submitted:
        return Icons.send;
      case ActionType.emailSent:
        return Icons.email;
      case ActionType.formFilled:
        return Icons.description;
      case ActionType.mailSent:
        return Icons.mail;
      case ActionType.responseReceived:
        return Icons.inbox;
      case ActionType.completed:
        return Icons.check_circle;
      case ActionType.failed:
        return Icons.error;
      case ActionType.noteAdded:
        return Icons.note;
    }
  }

  void _showDeleteConfirmation(OptOutRequest request) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Request?'),
        content: Text(
          'Are you sure you want to delete the opt-out request for ${request.brokerName}?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () async {
              Navigator.pop(context);
              await _deleteRequest(request);
            },
            style: FilledButton.styleFrom(
              backgroundColor: Colors.red,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteRequest(OptOutRequest request) async {
    try {
      final storageService = context.read<StorageService>();
      await storageService.deleteRequest(request.id);
      await _loadRequests();

      if (!mounted) return;
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Request deleted'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to delete request: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
}
