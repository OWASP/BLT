import 'package:flutter/material.dart';

final Map<int, String> labels = {
  0: "General",
  1: "Number error",
  2: "Functional",
  3: "Performance",
  4: "Security",
  5: "Type",
  6: "Design",
  7: "Server down",
};

// final Map<int, Color> labelColors = {
//   0: Colors.blue.shade700,
//   1: Colors.orange.shade600,
//   2: Colors.purple.shade600,
//   3: Colors.yellow.shade800,
//   4: Colors.indigo.shade600,
//   5: Colors.teal.shade700,
//   6: Colors.brown.shade600,
//   7: Colors.grey.shade600,
// };

Color getLabelColor(int index) {
  switch (index) {
    case 0:
      return Colors.blue.shade700;
    case 1:
      return Colors.orange.shade600;
    case 2:
      return Colors.purple.shade600;
    case 3:
      return Colors.yellow.shade800;
    case 4:
      return Colors.indigo.shade600;
    case 5:
      return Colors.teal.shade700;
    case 6:
      return Colors.brown.shade600;
    case 7:
      return Colors.grey.shade600;
    default:
      return Colors.white;
  }
}
