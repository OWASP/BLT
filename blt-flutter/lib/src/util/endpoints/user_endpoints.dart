import 'general_endpoints.dart';

/// Class for API endpoints needed to access users data on BLT.
class UserEndPoints {
  UserEndPoints._();

  static const String userInfo = GeneralEndPoints.apiBaseUrl + "profile/";

  static const String userData = GeneralEndPoints.apiBaseUrl + "profile/auth/user/";
}
