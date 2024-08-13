import 'package:blt/src/util/util_import.dart';
import 'package:http/http.dart' as http;

class TagsApiClient {
  TagsApiClient._();
  static Future<List<Tag>> getListOfTags() async {
    List<Tag> tags = [];
    try {
      var response = await http.get(
        Uri.parse(GeneralEndPoints.apiBaseUrl + "tags"),
        headers: {"content-type": "application/json"},
      );
      var json = jsonDecode(response.body);
      tags = Tag.fromSnapshot(json["results"]);
    } catch (e) {
      print(e);
    }
    return tags;
  }

  Future<void> postTag(String name, BuildContext context) async {
    try {
      var response = await http.post(
        Uri.parse(GeneralEndPoints.apiBaseUrl + "tags"),
        headers: {"content-type": "application/json"},
        body: {"name": name},
      );
      if (response.statusCode == 201 || response.statusCode == 200) {
        SnackBar thankSnack = SnackBar(
          content: Text("New tag created successfully!"),
        );
        ScaffoldMessenger.of(context).showSnackBar(thankSnack);
      } else {
        ScaffoldMessenger.of(context).clearSnackBars();
        SnackBar errorSnack = SnackBar(
          content:
              Text("There was some error, please try again!" + response.body),
        );
        print(response.body);
        ScaffoldMessenger.of(context).showSnackBar(errorSnack);
      }
    } catch (e) {
      print(e);
    }
  }
}
