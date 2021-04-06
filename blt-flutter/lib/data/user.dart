class User {
  int? id;
  String? username;
  String? token;

  User({
    this.id,
    this.username,
    this.token,
  });

  factory User.fromJson(Map<String, dynamic> responseData) {
    return User(
      id: responseData['id'],
      username: responseData['username'],
      token: responseData['token'],
    );
  }
}
