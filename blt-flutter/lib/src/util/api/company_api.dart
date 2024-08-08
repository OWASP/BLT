import 'package:blt/src/util/util_import.dart';
import 'package:http/http.dart' as http;

/// CLass for accessing the company client.
class CompanyApiClient {
  CompanyApiClient._();

  static Future<List<Company>> getListOfCompanies(
      http.Client client, String endpoint) async {
    String searchUrl = GeneralEndPoints.apiBaseUrl + endpoint;
    List<Company> companiesList = [];
    try {
      var response = await client.get(Uri.parse(searchUrl));
      var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
      companiesList = Company.fromSnapshot(decodedResponse["results"]);
    } catch (e) {
      print(e);
    }
    return companiesList;
  }

  /// Search a company by keyword,
  /// returns the first matching result.
  static Future<Company?> getCompanyByKeyWord(
      http.Client client, String paginated_url, String keyword) async {
    String searchUrl = paginated_url + "?search=$keyword";
    // print(searchUrl);
    try {
      var response = await client.get(Uri.parse(searchUrl));
      var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
      var companyJson = Company.fromJson(decodedResponse["results"][0]);
      return companyJson;
    } catch (e) {
      print(e);
    }
    return null;
  }
}
