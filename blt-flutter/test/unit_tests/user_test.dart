import '../test_imports.dart';
import 'package:http/http.dart' as http;

void main() {
  setUp(() {
    currentUser = guestUser;
  });
  group("User Api's Test", () {
    test('Get User Info', () async {
      // Mock response data
      final dynamic mockResponse = {
        'count': 1,
        "results": [
          {
            'username': 'test_user',
            'token': 'test_token',
            'other_data': 'test_data',
            'description': 'description',
            'email': 'test@gmail.com',
          }
        ]
      };

      final user = User();
      user.id = 1;
      user.username = 'test_user';
      user.token = 'test_token';

      final client = MockClient((request) async {
        if (request.headers['Authorization'] == 'Token test_token') {
          return http.Response(jsonEncode(mockResponse), 200);
        } else {
          return http.Response('Unauthorized', 401);
        }
      });

      final responseUser = await UserApiClient.getUserInfo(client, user);
      expect(responseUser?.username, 'test_user');
      expect(responseUser?.description, 'description');
      expect(responseUser?.email, 'test@gmail.com');
      expect(responseUser?.token, 'test_token');
    });
  });
}
