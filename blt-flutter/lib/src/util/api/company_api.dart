import 'dart:convert';

import 'package:bugheist/src/util/endpoints/company_endpoints.dart';
import 'package:http/http.dart' as http;

import '../../models/company_model.dart';

/// CLass for accessing the company client.
class CompanyApiClient {
  CompanyApiClient._();

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
