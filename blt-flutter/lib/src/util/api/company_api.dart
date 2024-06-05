import 'dart:convert';
import 'package:blt/src/util/util_import.dart';
import 'package:http/http.dart' as http;

/// CLass for accessing the company client.
class CompanyApiClient {
  CompanyApiClient._();

  static Future<List<Company>> getListOfCompanies(String endpoint) async {
    String searchUrl = GeneralEndPoints.apiBaseUrl + endpoint;
    List<Company> companiesList = [];
    try {
      var response = await http.get(Uri.parse(searchUrl));
      var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
      companiesList = Company.fromSnapshot(decodedResponse["results"]);
    } catch (e) {
      print(e);
    }
    return companiesList;
  }

  /// Search a company by keyword,
  /// returns the first matching result.
  static Future<void> getCompanyByKeyWord(
    Company company,
    String keyword,
  ) async {
    http.Response? response;
    String searchUrl = CompanyEndpoints.domain + "?search=$keyword";
    try {
      response = await http.get(Uri.parse(searchUrl));
      var decodedResponse = jsonDecode(utf8.decode(response.bodyBytes));
      var companyJson = decodedResponse["results"][0];
      company.setMoreInfo(
        companyJson["id"],
        companyJson["email"],
        companyJson["url"],
        companyJson["color"],
      );
    } catch (e) {
      print(e);
    }
  }
}
