import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/issue_model.dart';
import '../providers/login_provider.dart';
import '../util/api/issues_api.dart';
import '../util/enums/login_type.dart';

/// Issue flags show and toggle component.
class IssueFlagButton extends ConsumerStatefulWidget {
  final Issue issue;
  final Color? color;
  const IssueFlagButton({
    Key? key,
    this.color,
    required this.issue,
  }) : super(key: key);

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _IssueFlagButtonState();
}

class _IssueFlagButtonState extends ConsumerState<IssueFlagButton> {
  late int flags;
  late bool flagged;

  Future<void> toggleIssueFlag() async {
    setState(() {
      if (flagged) {
        flags = flags - 1;
      } else {
        flags = flags + 1;
      }
      flagged = !flagged;
    });

    try {
      bool status = await IssueApiClient.toggleIssueLikes(widget.issue.id!);
      if (!status) {
        setState(() {
          flags = widget.issue.flags!;
          flagged = widget.issue.flagged!;
        });
      } else {
        widget.issue.likes = flags;
        widget.issue.flagged = flagged;
      }
    } catch (e) {
      print(e);
    }
  }

  @override
  void initState() {
    super.initState();
    flagged = widget.issue.flagged!;
    flags = widget.issue.flags!;
  }

  @override
  Widget build(BuildContext context) {
    return TextButton.icon(
      onPressed: () async {
        if (ref.read(loginProvider.notifier).loginType == LoginType.guest) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text("Login to like and flag issues!"),
            ),
          );
        } else {
          await toggleIssueFlag();
        }
      },
      icon: Icon(
        Icons.flag_outlined,
        color: widget.color,
      ),
      label: Text(
        "${flags}",
        style: TextStyle(
          color: widget.color,
        ),
      ),
    );
  }
}
