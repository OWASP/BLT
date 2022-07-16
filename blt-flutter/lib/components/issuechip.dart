import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../models/issue_model.dart';

class IssueStatusChip extends StatelessWidget {
  final Issue issue;
  const IssueStatusChip({
    Key? key,
    required this.issue,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Chip(
      label: Text(
        (issue.isOpen) ? "Open" : "Closed",
        style: GoogleFonts.aBeeZee(
          textStyle: TextStyle(
            fontSize: 10,
            color: (issue.isOpen) ? Color(0xFFA3A3A3) : Color(0xFFDC4654),
          ),
        ),
      ),
    );
  }
}
