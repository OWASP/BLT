import 'package:blt/src/components/components_import.dart';
import 'package:blt/src/util/brand.dart';

/// The app's main Appbar
AppBar buildAppBar({required BuildContext context}) {
  final isDarkMode = Theme.of(context).brightness == Brightness.dark;
  return AppBar(
    title: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        SvgPicture.asset(
          'assets/blt_wasp.svg',
          height: 30,
          semanticsLabel: 'OWASP BLT',
        ),
        const SizedBox(width: 8),
        Text(
          'BLT',
          style: TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 22,
            color: isDarkMode ? Colors.white : BLTColors.gray900,
          ),
        ),
      ],
    ),
    actions: <Widget>[
      IconButton(
        icon: Icon(
          Icons.search,
          color: isDarkMode ? Colors.grey[350] : BLTColors.primary,
        ),
        onPressed: () {
          showSearch(
            context: context,
            delegate: BLTSearchDelegate(),
          );
        },
      ),
      IconButton(
        icon: Icon(
          Icons.account_circle,
          color: isDarkMode ? Colors.grey[350] : BLTColors.primary,
        ),
        onPressed: () {
          if (currentUser!.id == null) {
            ScaffoldMessenger.of(context).showSnackBar(SnackBar(
              content: const Text("No profile Found Check Your Connection"),
            ));
            return;
          }
          Navigator.of(context).pushNamed(
            RouteManager.profilePage,
          );
        },
      )
    ],
    elevation: 0,
    backgroundColor: isDarkMode
        ? BLTColors.darkSurface
        : Theme.of(context).canvasColor,
    iconTheme: isDarkMode
        ? IconThemeData(color: Colors.grey[350])
        : IconThemeData(color: BLTColors.primary),
  );
}
