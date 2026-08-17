class LoginAnomaly {
  final String accountId;
  final double score;
  final String riskBand;
  final List<String> reasonCodes;
  final DateTime detectedAt;

  const LoginAnomaly({
    required this.accountId,
    required this.score,
    required this.riskBand,
    required this.reasonCodes,
    required this.detectedAt,
  });
}
