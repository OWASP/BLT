import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class IssueLikeButton extends ConsumerStatefulWidget {
  const IssueLikeButton({Key? key}) : super(key: key);

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _IssueLikeButtonState();
}

class _IssueLikeButtonState extends ConsumerState<IssueLikeButton> {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 25,
      child: Row(
        children: [
          IconButton(
            onPressed: () {},
            icon: Icon(
              Icons.favorite,
            ),
          ),
          Text(""),
        ],
      ),
    );
  }
}
