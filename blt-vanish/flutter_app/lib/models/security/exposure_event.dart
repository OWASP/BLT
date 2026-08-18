class ExposureEvent {
  final String id;
  final String source;
  final String urgency;
  final DateTime occurredAt;

  const ExposureEvent({
    required this.id,
    required this.source,
    required this.urgency,
    required this.occurredAt,
  });
}
