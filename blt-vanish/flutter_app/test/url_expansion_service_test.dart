import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:selferase/services/url_expansion_service.dart';

void main() {
  group('UrlExpansionService', () {
    test('resolves redirect chains up to the final reachable destination', () async {
      final mockClient = MockClient((request) async {
        if (request.url.toString() == 'https://bit.ly/short') {
          return http.Response(
            '',
            301,
            headers: {'location': '/hop-1'},
            request: request,
          );
        }

        if (request.url.toString() == 'https://bit.ly/hop-1') {
          return http.Response(
            '',
            302,
            headers: {'location': 'https://target.example/login'},
            request: request,
          );
        }

        return http.Response('', 200, request: request);
      });

      final service = UrlExpansionService(client: mockClient);
      final result = await service.expandUrl('https://bit.ly/short');

      expect(result, 'https://target.example/login');
    });

    test('returns the last stable URL when redirect headers are malformed', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          '',
          302,
          headers: {'location': ''},
          request: request,
        );
      });

      final service = UrlExpansionService(client: mockClient);
      final result = await service.expandUrl('https://safe.example/start');

      expect(result, 'https://safe.example/start');
    });

    test('falls back to the last resolved hop on timeout', () async {
      final mockClient = MockClient((request) async {
        if (request.url.toString() == 'https://bit.ly/short') {
          return http.Response(
            '',
            301,
            headers: {'location': 'https://target.example/intermediate'},
            request: request,
          );
        }

        await Future<void>.delayed(const Duration(milliseconds: 700));
        return http.Response('', 200, request: request);
      });

      final service = UrlExpansionService(client: mockClient);
      final result = await service.expandUrl('https://bit.ly/short');

      expect(result, 'https://target.example/intermediate');
    });
  });
}
