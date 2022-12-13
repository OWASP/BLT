import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class IssueFlagButton extends ConsumerStatefulWidget {
  const IssueFlagButton({Key? key}) : super(key: key);

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _IssueFlagButtonState();
}

class _IssueFlagButtonState extends ConsumerState<IssueFlagButton> {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 25,
      child: Row(
        children: [
          IconButton(
            onPressed: () {},
            icon: Icon(
              Icons.bookmark,
            ),
          ),
          Text(""),
        ],
      ),
    );
  }
}
