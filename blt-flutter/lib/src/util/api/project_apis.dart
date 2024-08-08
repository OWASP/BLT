import 'package:blt/src/models/project_model.dart';
import 'package:http/http.dart' as http;

import '../util_import.dart';

class ProjectAPiClient {
  ProjectAPiClient._();

  static Future<List<Project>?> getAllProjects(
      {http.Client? testClient}) async {
    List<Project> projects = [];
    try {
      var uri = GeneralEndPoints.apiBaseUrl + "projects/";
      var response = (testClient != null)
          ? await testClient.get(Uri.parse(uri))
          : await http.get(Uri.parse(uri));
      var json_res = json.decode(response.body);
      projects = Project.fromSnapshot(json_res['projects']);
    } catch (e) {
      print(projects);
      print(e);
    }
    return projects;
  }
}
