import 'dart:convert';
import 'package:blt/src/pages/home/home_imports.dart';
import 'package:http/http.dart' as http;

class ChatBotApiClient {
  ChatBotApiClient._();

  static Future<String> getResponse(String query) async {
    try {
      var response = await http.post(
        Uri.parse("${GeneralEndPoints}/api/chatbot/conversation/"),
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
