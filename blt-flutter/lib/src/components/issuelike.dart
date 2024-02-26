import 'package:flutter/material.dart';
import 'package:blt/src/components/components_import.dart';

/// Issue likes show and toggle component.
class IssueLikeButton extends ConsumerStatefulWidget {
  final Issue issue;
  final Color? color;

  const IssueLikeButton({
    Key? key,
    required this.issue,
    this.color,
  }) : super(key: key);

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _IssueLikeButtonState();
}

class _IssueLikeButtonState extends ConsumerState<IssueLikeButton> {
  late int likes;
  late bool liked;

  Future<void> toggleIssueLike() async {
    setState(() {
      if (liked) {
        likes = likes - 1;
      } else {
        likes = likes + 1;
      }
      liked = !liked;
    });

    try {
      bool status = await IssueApiClient.toggleIssueLikes(widget.issue.id!);
      if (!status) {
        setState(() {
          likes = widget.issue.likes!;
          liked = widget.issue.liked!;
        });
      } else {
        widget.issue.likes = likes;
        widget.issue.liked = liked;
      }
    } catch (e) {
      print(e);
    }
  }

  @override
  void initState() {
    super.initState();
    liked = widget.issue.liked!;
    likes = widget.issue.likes!;
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
          await toggleIssueLike();
        }
      },
      icon: Icon(
        (liked) ? Icons.favorite : Icons.favorite_border_rounded,
        color: widget.color,
      ),
      label: Text(
        "$likes",
        style: TextStyle(
          color: widget.color,
        ),
      ),
    );
  }
}
