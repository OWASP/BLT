import 'package:blt/src/providers/providers_imports.dart';
import 'package:blt/src/util/api/project_apis.dart';

final projectListProvider =
    StateNotifierProvider<ProjectListProvider, AsyncValue<List<Project>?>?>(
        (ref) {
  return ProjectListProvider(ref.read);
});

class ProjectListProvider extends StateNotifier<AsyncValue<List<Project>?>?> {
  final Reader read;
  AsyncValue<List<Project>?>? previousState;

  ProjectListProvider(this.read, [AsyncValue<List<Project>>? projectList])
      : super(projectList ?? const AsyncValue.loading()) {
    _retrieveProjectList();
  }

  Future<void> _retrieveProjectList() async {
    try {
      final List<Project>? projects = await ProjectAPiClient.getAllProjects();
      state = AsyncValue.data(projects);
    } catch (e) {
      AsyncValue.error(e);
    }
  }

  Future<void> refreshProjectList() async {
    state = const AsyncValue.loading();
    try {
      await _retrieveProjectList();
    } catch (e) {
      AsyncValue.error(e);
    }
  }
}
