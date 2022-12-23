/// Model class for a user signed up on BugHeist.
class User {
  int? id;
  String? username;
  String? token;
  String? email;
  String? pfpLink;
  int? title;
  String? description;
  String? winning;
  List<int>? following;
  List<int>? upvotedIssueId;
  List<int>? savedIssueId;

  User({
    this.id,
    this.username,
    this.token,
    this.email,
    this.pfpLink,
    this.title,
    this.description,
    this.winning,
    this.following,
    this.upvotedIssueId,
    this.savedIssueId,
  });

  factory User.fromJson(Map<String, dynamic> responseData, String accessToken) {
    return User(
      id: responseData['pk'],
      username: responseData['username'],
      email: responseData['email'],
      token: accessToken,
      pfpLink: responseData["user_avatar"],
      description: responseData["description"],
      winning: responseData["winnings"],
      following: responseData["follows"],
      upvotedIssueId: responseData["issue_upvoted"],
      savedIssueId: responseData["issue_saved"],
    );
  }
}

/// The [User] instance used for anonymous login.
User guestUser = User(
  id: 1234567890,
  username: "Anonymous",
  token: "anonymousuest@987654321",
  email: "anonymous@gmail.com",
  pfpLink:
      "https://secure.gravatar.com/avatar/3633ff387ed54aa6d8e9a1593192b8de.jpg?s=200&d=mm&r=g",
  description: "I like to stay anonymous!",
  following: [],
  upvotedIssueId: [1, 2, 3, 4, 5, 6],
  savedIssueId: [],
);
