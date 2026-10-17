import 'package:blt/src/components/components_import.dart';

/// The app's main Appbar
AppBar buildAppBar({required BuildContext context}) {
  final isDarkMode = Theme.of(context).brightness == Brightness.dark;
  return AppBar(
    title: SvgPicture.asset(
      isDarkMode ? 'assets/blt_logo_dark.svg' : 'assets/blt_logo.svg',
      fit: BoxFit.cover,
      height: 30,
    ),
    actions: <Widget>[
      IconButton(
        icon: Icon(
          Icons.search,
          color: isDarkMode ? Colors.grey[350] : Colors.red,
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
          color: isDarkMode ? Colors.grey[350] : Colors.red,
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
        ? Color.fromRGBO(58, 21, 31, 1)
        : Theme.of(context).canvasColor,
    iconTheme: isDarkMode
        ? IconThemeData(color: Colors.grey[350])
        : IconThemeData(color: Color(0xFFDC4654)),
  );
}
