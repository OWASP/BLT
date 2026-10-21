import 'package:blt/src/components/components_import.dart';
import 'package:blt/src/util/brand.dart';

/// Chip that shows the open/close status of an issue.
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
        style: BLTFonts.system(
          textStyle: TextStyle(
            fontSize: 10,
            color: (issue.isOpen) ? BLTColors.gray400 : BLTColors.primary,
          ),
        ),
      ),
    );
  }
}
