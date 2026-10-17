import 'dart:convert';
import 'package:blt/src/pages/home/home_imports.dart';
import 'package:http/http.dart' as http;

class ChatBotApiClient {
  ChatBotApiClient._();

  static Future<String> getResponse(String query) async {
    try {
      var link = GeneralEndPoints.baseUrl + "api/chatbot/conversation/";
      var response = await http.post(
        Uri.parse(link),
        headers: {"parses": "application/json", "renders": "application/json"},
        body: {"question": query},
      );

      var json = jsonDecode(response.body);
      if (json["answer"] == "" || json["answer"] == null)
        return "err: ${json["error"]}";

      return "res: ${json["answer"]}";
    } catch (e) {
      return "err: $e";
    }
  }
}
