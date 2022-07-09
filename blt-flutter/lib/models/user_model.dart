class User {
  int? id;
  String? username;
  String? token;
  String? email;

  User({
    this.id,
    this.username,
    this.token,
    this.email,
  });

  factory User.fromJson(Map<String, dynamic> responseData, String accessToken) {
    return User(
      id: responseData['pk'],
      username: responseData['username'],
      email: responseData['email'],
      token: accessToken,
    );
  }
}

User guestUser = User(
  id: 1234567890,
  username: "Anonymous",
  email: "anonymous@gmail.com",
);
