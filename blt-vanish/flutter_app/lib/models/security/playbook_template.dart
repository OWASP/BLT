class PlaybookStep {
  final String id;
  final String title;
  final String description;
  final String actionType;
  final bool isRequired;

  const PlaybookStep({
    required this.id,
    required this.title,
    required this.description,
    required this.actionType,
    required this.isRequired,
  });
}

class PlaybookTemplate {
  final String id;
  final String title;
  final String severityTrigger;
  final List<PlaybookStep> steps;

  const PlaybookTemplate({
    required this.id,
    required this.title,
    required this.severityTrigger,
    required this.steps,
  });
}
