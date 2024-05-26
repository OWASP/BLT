import 'package:blt/src/components/components_import.dart';
import 'package:blt/src/models/company_model.dart';
import 'package:blt/src/util/api/company_api.dart';

final companiesListProvider =
    StateNotifierProvider<CompanyListNotifier, AsyncValue<List<Company>?>?>(
  (ref) {
    return CompanyListNotifier(ref.read);
  },
);

class CompanyListNotifier extends StateNotifier<AsyncValue<List<Company>?>?> {
  final Reader read;
  AsyncValue<List<Company>?>? previousState;

  CompanyListNotifier(this.read, [AsyncValue<List<Company>>? companyList])
      : super(companyList ?? const AsyncValue.loading()) {
    _retrieveCompaniesList();
  }

  Future<void> _retrieveCompaniesList() async {
    try {
      final List<Company>? companyData =
          await CompanyApiClient.getListOfCompanies("/company/");
      state = AsyncValue.data(companyData);
    } catch (e) {
      AsyncValue.error(e);
    }
  }

  Future<void> refreshCompanyList() async {
    state = const AsyncValue.loading();
    try {
      await _retrieveCompaniesList();
    } catch (e) {
      AsyncValue.error(e);
    }
  }
}
