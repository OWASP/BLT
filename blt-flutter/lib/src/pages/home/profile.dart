import 'package:blt/src/pages/home/home_imports.dart';
import 'package:http/http.dart' as http;
import 'package:blt/src/util/brand.dart';

/// Page that displays the stats of a user registered on BLT,
/// shows dummy data for Guest login.
class UserProfile extends ConsumerStatefulWidget {
  const UserProfile({
    Key? key,
    User? user,
  }) : super(key: key);

  @override
  ConsumerState<ConsumerStatefulWidget> createState() => _UserProfileState();
}

class _UserProfileState extends ConsumerState<UserProfile> {
  late Future<List<Issue>?> getLikedList;
  late Future<List<Issue>?> getSavedList;
  late Future<List<Issue>?> getFlaggedList;

  ImageProvider<Object> getProfilePicture() {
    if (currentUser!.pfpLink == null) {
      return AssetImage("assets/default_profile.png");
    } else {
      return NetworkImage(currentUser!.pfpLink!);
    }
  }

  Future<List<Issue>?> getAnonymousUserIssueList() async {
    List<Issue>? issueList = null;
    final client = http.Client();
    try {
      // final IssueData? issueData = await IssueApiClient.getAllIssues(
      //   client,
      //   IssueEndPoints.issues,
      // );
      // issueList = issueData!.issueList;
    } catch (e) {}
    return issueList;
  }

  Future<List<Issue>?> getIssueList(List<int>? idList) async {
    List<Issue>? issueList = null;
    try {
      if (idList != null) {
        issueList = [];
        for (int id in idList) {
          Issue? issue = await IssueApiClient.getIssueById(id);
          if (issue != null) issueList.add(issue);
        }
      }
    } catch (e) {}
    return issueList;
  }

  Future<void> forgetUser() async {
    await ref.read(authStateNotifier.notifier).forgetUser();
  }

  Future<void> logout() async {
    await ref.read(authStateNotifier.notifier).logout();
  }

  Widget buildLikedIssues(Size size, List<Issue>? issueList) {
    if (issueList != null && issueList.length > 0) {
      return Container(
        margin: EdgeInsets.symmetric(vertical: 20),
        decoration: BoxDecoration(
          border: Border.all(color: BLTColors.textMuted, width: 0.5),
          borderRadius: BorderRadius.circular(15),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(15),
          child: ConstrainedBox(
            constraints: BoxConstraints(
                minWidth: size.width, maxHeight: 0.75 * size.height),
            child: ListView.builder(
              shrinkWrap: true,
              padding: EdgeInsets.zero,
              itemCount: issueList.length,
              itemBuilder: (context, index) {
                Issue issue = issueList[index];
                return ListTile(
                  leading: Text("#${issue.id}"),
                  title: Text(
                    (issue.title.length < 24)
                        ? issue.title
                        : issue.title.substring(0, 24) + "...",
                  ),
                  trailing: IssueStatusChip(
                    issue: issue,
                  ),
                  onTap: () {
                    Navigator.pushNamed(
                      context,
                      RouteManager.issueDetailPage,
                      arguments: issue,
                    );
                  },
                );
              },
            ),
          ),
        ),
      );
    } else {
      return Container(
        margin: EdgeInsets.symmetric(vertical: 20),
        width: size.width,
        height: 0.3 * size.height,
        decoration: BoxDecoration(
          border: Border.all(color: BLTColors.textMuted, width: 0.5),
          borderRadius: BorderRadius.circular(15),
        ),
        child: Center(
          child: Text(
            AppLocalizations.of(context)!.noIssuesUpvoted,
            style: BLTFonts.system(
              textStyle: TextStyle(
                color: BLTColors.textMuted,
              ),
            ),
          ),
        ),
      );
    }
  }

  Widget buildFlaggedIssues(Size size, List<Issue>? issueList) {
    if (issueList != null && issueList.length > 0) {
      return Container(
        margin: EdgeInsets.symmetric(vertical: 20),
        decoration: BoxDecoration(
          border: Border.all(color: BLTColors.textMuted, width: 0.5),
          borderRadius: BorderRadius.circular(15),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(15),
          child: ConstrainedBox(
            constraints: BoxConstraints(
                minWidth: size.width, maxHeight: 0.75 * size.height),
            child: ListView.builder(
              shrinkWrap: true,
              padding: EdgeInsets.zero,
              itemCount: issueList.length,
              itemBuilder: (context, index) {
                Issue issue = issueList[index];
                return ListTile(
                  leading: Text("#${issue.id}"),
                  title: Text(
                    (issue.title.length < 24)
                        ? issue.title
                        : issue.title.substring(0, 24) + "...",
                  ),
                  trailing: IssueStatusChip(
                    issue: issue,
                  ),
                  onTap: () {
                    Navigator.pushNamed(
                      context,
                      RouteManager.issueDetailPage,
                      arguments: issue,
                    );
                  },
                );
              },
            ),
          ),
        ),
      );
    } else {
      return Container(
        margin: EdgeInsets.symmetric(vertical: 20),
        width: size.width,
        height: 0.3 * size.height,
        decoration: BoxDecoration(
          border: Border.all(color: BLTColors.textMuted, width: 0.5),
          borderRadius: BorderRadius.circular(15),
        ),
        child: Center(
          child: Text(
            AppLocalizations.of(context)!.noIssuesFlagged,
            style: BLTFonts.system(
              textStyle: TextStyle(
                color: BLTColors.textMuted,
              ),
            ),
          ),
        ),
      );
    }
  }

  Widget buildSavedIssues(Size size, List<Issue>? issueList) {
    if (issueList != null && issueList.length > 0) {
      return Container(
        margin: EdgeInsets.symmetric(vertical: 20),
        decoration: BoxDecoration(
          border: Border.all(color: BLTColors.textMuted, width: 0.5),
          borderRadius: BorderRadius.circular(15),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(15),
          child: ConstrainedBox(
            constraints: BoxConstraints(
                minWidth: size.width, maxHeight: 0.75 * size.height),
            child: ListView.builder(
              shrinkWrap: true,
              padding: EdgeInsets.zero,
              itemCount: issueList.length,
              itemBuilder: (context, index) {
                Issue issue = issueList[index];
                return ListTile(
                  leading: Text("#${issue.id}"),
                  title: Text(
                    (issue.title.length < 24)
                        ? issue.title
                        : issue.title.substring(0, 24) + "...",
                  ),
                  trailing: IssueStatusChip(
                    issue: issue,
                  ),
                  onTap: () {
                    Navigator.pushNamed(
                      context,
                      RouteManager.issueDetailPage,
                      arguments: issue,
                    );
                  },
                );
              },
            ),
          ),
        ),
      );
    } else {
      return Container(
        margin: EdgeInsets.symmetric(vertical: 20),
        width: size.width,
        height: 0.3 * size.height,
        decoration: BoxDecoration(
          border: Border.all(color: BLTColors.textMuted, width: 0.5),
          borderRadius: BorderRadius.circular(15),
        ),
        child: Center(
          child: Text(
            AppLocalizations.of(context)!.noIssuesSaved,
            style: BLTFonts.system(
              textStyle: TextStyle(
                color: BLTColors.textMuted,
              ),
            ),
          ),
        ),
      );
    }
  }

  void buildDeleteDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          "This account will be deleted permanently !",
          style: BLTFonts.system(
            textStyle: TextStyle(
              color: BLTColors.primary,
              fontSize: 15,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        content: Container(
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              TextButton(
                  onPressed: () async {
                    bool success = await AuthApiClient.delete();
                    if (success) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text("Account deleted successfully."),
                        ),
                      );
                      await forgetUser();
                      await Navigator.of(context).pushAndRemoveUntil(
                          MaterialPageRoute(
                              builder: (context) => WelcomePage()),
                          (Route route) => false);
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text("Error deleting this account."),
                        ),
                      );
                    }
                  },
                  style: ButtonStyle(
                    alignment: Alignment.center,
                    backgroundColor: WidgetStateProperty.all(BLTColors.primary),
                  ),
                  child: Text(
                    "Delete",
                    style: BLTFonts.system(
                      textStyle: TextStyle(
                        color: Color.fromRGBO(255, 255, 255, 1),
                        fontSize: 15,
                      ),
                    ),
                  )),
              TextButton(
                  onPressed: () {
                    Navigator.pop(context);
                  },
                  style: ButtonStyle(
                    alignment: Alignment.center,
                    backgroundColor: WidgetStateProperty.all(BLTColors.textMuted),
                  ),
                  child: Text(
                    AppLocalizations.of(context)!.cancel,
                    style: BLTFonts.system(
                      textStyle: TextStyle(
                        color: Color.fromRGBO(255, 255, 255, 1),
                        fontSize: 15,
                      ),
                    ),
                  )),
            ],
          ),
        ),
      ),
    );
  }

  @override
  void initState() {
    getLikedList = (currentUser! == guestUser)
        ? getAnonymousUserIssueList()
        : getIssueList(
            currentUser!.likedIssueId != null
                ? (currentUser!.likedIssueId!.length > 0
                    ? currentUser!.likedIssueId!
                    : null)
                : null,
          );
    getSavedList = (currentUser! == guestUser)
        ? getAnonymousUserIssueList()
        : getIssueList(
            currentUser!.savedIssueId != null
                ? (currentUser!.savedIssueId!.length > 0
                    ? currentUser!.savedIssueId!
                    : null)
                : null,
          );
    getFlaggedList = (currentUser! == guestUser)
        ? getAnonymousUserIssueList()
        : getIssueList(
            currentUser!.flaggedIssueId != null
                ? (currentUser!.flaggedIssueId!.length > 0
                    ? currentUser!.flaggedIssueId!
                    : null)
                : null,
          );
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: IconButton(
          icon: Icon(
            Icons.arrow_back_ios_new_rounded,
          ),
          onPressed: () {
            Navigator.of(context).pop();
          },
        ),
        title: Text(currentUser!.username!),
        actions: [
          IconButton(
            onPressed: () async {
              await forgetUser();
              await Navigator.of(context).pushAndRemoveUntil(
                MaterialPageRoute(
                  builder: (context) => WelcomePage(),
                ),
                (Route route) => false,
              );
              await logout();
            },
            icon: Icon(Icons.power_settings_new_rounded),
          ),
          PopupMenuButton<String>(
            onSelected: (String value) async {
              switch (value) {
                case 'Change picture':
                  final ImagePicker _picker = ImagePicker();
                  final XFile? image =
                      await _picker.pickImage(source: ImageSource.gallery);
                  if (image == null) {
                    return;
                  }
                  SnackBar updatingSnack = SnackBar(
                    duration: const Duration(seconds: 6),
                    content: Text(
                        AppLocalizations.of(context)!.updatingProfilePicture),
                  );
                  ScaffoldMessenger.of(context).showSnackBar(updatingSnack);
                  await UserApiClient.updatePfp(image, currentUser!);
                  setState(() {});
                  break;

                case 'Change password':
                  Navigator.pushNamed(context, RouteManager.changePassword);
              }
            },
            itemBuilder: (BuildContext context) {
              List<String> optionsList = ['Change picture'];
              LoginType loginState = ref.watch(loginProvider);
              if (loginState != LoginType.guest) {
                optionsList.add('Change password');
              }
              return optionsList.map((String choice) {
                return PopupMenuItem<String>(
                  value: choice,
                  child: Text(choice),
                );
              }).toList();
            },
          ),
        ],
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              BLTColors.textMuted.withOpacity(0.125),
              Colors.transparent,
            ],
          ),
        ),
        width: size.width,
        height: size.height,
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                width: size.width,
                height: 0.25 * size.height,
                decoration: BoxDecoration(
                  color: BLTColors.primary,
                  image: DecorationImage(
                    image: getProfilePicture(),
                    fit: BoxFit.cover,
                  ),
                  boxShadow: [BoxShadow(blurRadius: 7.0, color: Colors.black)],
                ),
              ),
              Container(
                padding: EdgeInsets.fromLTRB(20, 10, 20, 20),
                width: size.width,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      currentUser!.username!,
                      style: BLTFonts.system(
                        textStyle: TextStyle(
                          color: BLTColors.primary,
                          fontWeight: FontWeight.bold,
                          fontSize: 30,
                        ),
                      ),
                    ),
                    Text(
                      '#${currentUser!.id!}',
                      style: BLTFonts.system(
                        textStyle: TextStyle(
                          color: BLTColors.textMuted.withOpacity(0.5),
                          fontStyle: FontStyle.italic,
                          fontSize: 10,
                        ),
                      ),
                    ),
                    SizedBox(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          vertical: 5.0,
                        ),
                        child: Text(
                          (currentUser!.description != null)
                              ? currentUser!.description!
                              : AppLocalizations.of(context)!
                                  .noDescriptionWriteOne,
                          style: BLTFonts.system(
                            textStyle: TextStyle(
                              color: BLTColors.textMuted,
                              fontSize: 15,
                            ),
                          ),
                        ),
                      ),
                    ),
                    SizedBox(
                      child: (currentUser!.following != null)
                          ? TextButton(
                              onPressed: () {},
                              child: Text(
                                currentUser!.following!.length.toString() +
                                    AppLocalizations.of(context)!.following,
                                style: BLTFonts.system(
                                  textStyle: TextStyle(
                                    color: BLTColors.primary,
                                    fontSize: 15,
                                  ),
                                ),
                              ),
                            )
                          : null,
                    ),
                    Divider(
                      thickness: 2,
                    ),
                    SizedBox(
                      child: (currentUser!.following != null)
                          ? TextButton(
                              onPressed: () {},
                              child: Text(
                                (currentUser!.totalScore != null)
                                    ? "${AppLocalizations.of(context)!.score} : ${currentUser!.totalScore!} "
                                    : "${AppLocalizations.of(context)!.score} : 0 ",
                                style: BLTFonts.system(
                                  textStyle: TextStyle(
                                    color: BLTColors.primary,
                                    fontSize: 15,
                                  ),
                                ),
                              ),
                            )
                          : null,
                    ),
                    Divider(
                      thickness: 2,
                    ),
                  ],
                ),
              ),
              Container(
                padding: EdgeInsets.symmetric(
                  horizontal: 20,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.event_repeat,
                          color: BLTColors.textMuted,
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(
                            vertical: 8.0,
                            horizontal: 8,
                          ),
                          child: Text(
                            AppLocalizations.of(context)!.recentActivity,
                            style: BLTFonts.system(
                              textStyle: TextStyle(
                                color: BLTColors.textMuted,
                                fontWeight: FontWeight.bold,
                                fontSize: 20,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                    Row(
                      children: [
                        Padding(
                          padding: const EdgeInsets.all(5.0),
                          child: Icon(
                            Icons.favorite,
                            color: BLTColors.primary,
                          ),
                        ),
                        Text(
                          AppLocalizations.of(context)!.likedIssues,
                          style: BLTFonts.system(
                            textStyle: TextStyle(
                              color: BLTColors.primary,
                              fontSize: 17.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                    Divider(
                      color: BLTColors.primary,
                      thickness: 2,
                    ),
                    FutureBuilder<List<Issue>?>(
                      future: getLikedList,
                      builder: ((context, snapshot) {
                        if (snapshot.connectionState ==
                            ConnectionState.waiting) {
                          return Container(
                            margin: EdgeInsets.symmetric(vertical: 20),
                            width: size.width,
                            height: 0.3 * size.height,
                            decoration: BoxDecoration(
                              border: Border.all(
                                color: BLTColors.textMuted,
                              ),
                              borderRadius: BorderRadius.circular(15),
                            ),
                            child: Center(
                              child: CircularProgressIndicator(),
                            ),
                          );
                        } else {
                          return buildLikedIssues(size, snapshot.data);
                        }
                      }),
                    ),
                    Row(
                      children: [
                        Padding(
                          padding: const EdgeInsets.all(5.0),
                          child: Icon(
                            Icons.flag,
                            color: BLTColors.primary,
                          ),
                        ),
                        Text(
                          AppLocalizations.of(context)!.flaggedIssues,
                          style: BLTFonts.system(
                            textStyle: TextStyle(
                              color: BLTColors.primary,
                              fontSize: 17.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                    Divider(
                      color: BLTColors.primary,
                      thickness: 2,
                    ),
                    FutureBuilder<List<Issue>?>(
                      future: getFlaggedList,
                      builder: ((context, snapshot) {
                        if (snapshot.connectionState ==
                            ConnectionState.waiting) {
                          return Container(
                            margin: EdgeInsets.symmetric(vertical: 20),
                            width: size.width,
                            height: 0.3 * size.height,
                            decoration: BoxDecoration(
                              border: Border.all(
                                color: BLTColors.textMuted,
                              ),
                              borderRadius: BorderRadius.circular(15),
                            ),
                            child: Center(
                              child: CircularProgressIndicator(),
                            ),
                          );
                        } else {
                          return buildFlaggedIssues(size, snapshot.data);
                        }
                      }),
                    ),
                    Row(
                      children: [
                        Padding(
                          padding: const EdgeInsets.all(5.0),
                          child: Icon(
                            Icons.bookmark_outlined,
                            color: BLTColors.primary,
                          ),
                        ),
                        Text(
                          AppLocalizations.of(context)!.savedIssues,
                          style: BLTFonts.system(
                            textStyle: TextStyle(
                              color: BLTColors.primary,
                              fontSize: 17.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                    Divider(
                      color: BLTColors.primary,
                      thickness: 2,
                    ),
                    FutureBuilder<List<Issue>?>(
                      future: getSavedList,
                      builder: ((context, snapshot) {
                        if (snapshot.connectionState ==
                            ConnectionState.waiting) {
                          return Container(
                            margin: EdgeInsets.symmetric(vertical: 20),
                            width: size.width,
                            height: 0.3 * size.height,
                            decoration: BoxDecoration(
                              border: Border.all(
                                color: BLTColors.textMuted,
                              ),
                              borderRadius: BorderRadius.circular(15),
                            ),
                            child: Center(
                              child: CircularProgressIndicator(),
                            ),
                          );
                        } else {
                          return buildSavedIssues(size, snapshot.data);
                        }
                      }),
                    ),
                    Center(
                      child: TextButton(
                        onPressed: () async {
                          if (currentUser == guestUser) {
                            ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text("Anonymous User !!")));
                          } else {
                            buildDeleteDialog(context);
                          }
                        },
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 20, vertical: 5),
                          child: Text(
                            "Delete Account",
                            style: BLTFonts.system(
                              textStyle: TextStyle(
                                color: Colors.white,
                                fontSize: 18,
                              ),
                            ),
                          ),
                        ),
                        style: ButtonStyle(
                          shape:
                              WidgetStateProperty.all<RoundedRectangleBorder>(
                            RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8.0),
                            ),
                          ),
                          backgroundColor: WidgetStateProperty.all(
                            isDarkMode
                                ? BLTColors.primaryDark
                                : BLTColors.primary,
                          ),
                        ),
                      ),
                    ),
                    SizedBox(height: 30),
                  ],
                ),
              )
            ],
          ),
        ),
      ),
    );
  }
}
