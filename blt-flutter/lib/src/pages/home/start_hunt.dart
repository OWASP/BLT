import 'dart:typed_data';
import 'package:blt/src/pages/home/home_imports.dart';
import 'package:path_provider/path_provider.dart';
import 'package:blt/src/util/brand.dart';

/// Start Bug Hunt Page
/// companies and individuals
/// should be able to start bughunts.
class StartHuntPage extends ConsumerStatefulWidget {
  const StartHuntPage({Key? key}) : super(key: key);

  @override
  ConsumerState<StartHuntPage> createState() => _StartHuntPageState();
}

class _StartHuntPageState extends ConsumerState<StartHuntPage> {
  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(horizontal: 20),
      child: HuntForm(),
    );
  }
}

class HuntForm extends StatefulWidget {
  const HuntForm({Key? key}) : super(key: key);

  @override
  State<HuntForm> createState() => _HuntFormState();
}

class _HuntFormState extends State<HuntForm> {
  late TextEditingController _websiteController;
  File _image = File("");
  final picker = ImagePicker();
  int prizeMoney = 100;

  Future<void> _pickImageFromGallery() async {
    try {
      final imageFile = await picker.pickImage(source: ImageSource.gallery);
      setState(() {
        if (imageFile != null) {
          if (mounted) {
            setState(() {
              _image = File(imageFile.path);
            });
          }
        } else {
          print('No image selected.');
        }
      });
    } catch (e) {
      print('Failed to pick image: $e');
    }
  }

  Future<File> _convertToImage(Uint8List imageBytes) async {
    String tempPath = (await getTemporaryDirectory()).path;
    File file = File('$tempPath/profile.png');
    await file.writeAsBytes(imageBytes.buffer
        .asUint8List(imageBytes.offsetInBytes, imageBytes.lengthInBytes));
    return file;
  }

  Future<void> _pasteImageFromClipBoard() async {
    try {
      final imageBytes = await Pasteboard.image;
      late File? image;
      if (imageBytes != null) {
        image = await _convertToImage(imageBytes);
      }
      setState(() {
        _image = image!;
      });
    } catch (e) {
      print('No Image Found On Clipboard');
    }
  }

  @override
  void initState() {
    super.initState();
    _websiteController = TextEditingController();
  }

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    return Form(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 12.0),
            child: Text(
              AppLocalizations.of(context)!.appNameOrURL,
              style: BLTFonts.system(
                textStyle: TextStyle(
                  color: BLTColors.primary,
                  fontSize: 15,
                ),
              ),
            ),
          ),
          SizedBox(
            height: 12,
          ),
          SizedBox(
            height: 40,
            child: TextFormField(
              controller: _websiteController,
              decoration: InputDecoration(
                hintText: AppLocalizations.of(context)!.enterURLorAppName,
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.all(
                    Radius.circular(8.0),
                  ),
                  borderSide: BorderSide(color: Colors.grey),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.all(
                    Radius.circular(8.0),
                  ),
                  borderSide: BorderSide(color: Colors.grey),
                ),
              ),
              cursorColor: BLTColors.primary,
              style: BLTFonts.system(
                textStyle: TextStyle(
                  fontSize: 12,
                ),
              ),
            ),
          ),
          Container(
            margin: const EdgeInsets.symmetric(vertical: 8.0),
            child: Row(
              children: [
                SizedBox(
                  child: TextButton(
                    child: Text(
                      AppLocalizations.of(context)!.chooseImage,
                      style: BLTFonts.system(
                        textStyle: TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                        ),
                      ),
                    ),
                    onPressed: () {
                      _pickImageFromGallery();
                    },
                    style: ButtonStyle(
                      backgroundColor: WidgetStateProperty.all(
                        isDarkMode
                            ? BLTColors.primaryDark
                            : BLTColors.primary,
                      ),
                    ),
                  ),
                ),
                SizedBox(
                  width: 10,
                ),
                SizedBox(
                  child: TextButton(
                    child: Text(
                      AppLocalizations.of(context)!.chooseFromClipboard,
                      style: BLTFonts.system(
                        textStyle: TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                        ),
                      ),
                    ),
                    onPressed: () {
                      _pasteImageFromClipBoard();
                    },
                    style: ButtonStyle(
                      backgroundColor: WidgetStateProperty.all(
                        isDarkMode
                            ? BLTColors.primaryDark
                            : BLTColors.primary,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          Container(
            height: 280,
            width: double.infinity,
            margin: const EdgeInsets.only(bottom: 12.0),
            child: _image.path == ""
                ? Center(
                    child: Text(
                      AppLocalizations.of(context)!.noImageSelected,
                      style: BLTFonts.system(
                        textStyle: TextStyle(
                          color: BLTColors.textMuted,
                        ),
                      ),
                    ),
                  )
                : Image.file(
                    _image,
                    fit: BoxFit.cover,
                  ),
            decoration: BoxDecoration(
              border: _image.path == ""
                  ? Border.all(
                      color: isDarkMode
                          ? BLTColors.primaryDark
                          : BLTColors.primary,
                      width: 0.5,
                    )
                  : null,
              borderRadius:
                  _image.path == "" ? BorderRadius.circular(15) : null,
            ),
          ),
          Container(
            margin: const EdgeInsets.only(bottom: 12.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  AppLocalizations.of(context)!.setPrizeMoney,
                  style: BLTFonts.system(
                    textStyle: TextStyle(
                      color: BLTColors.primary,
                      fontSize: 20,
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8.0),
                  child: Text(
                    AppLocalizations.of(context)!.rewardToUsersHuntingBugs,
                    style: BLTFonts.system(
                      textStyle: TextStyle(
                        color: BLTColors.textMuted,
                      ),
                    ),
                  ),
                ),
                Row(
                  children: [
                    Text(
                      "\$ $prizeMoney",
                      style: BLTFonts.system(
                        textStyle: TextStyle(
                            color: BLTColors.primary,
                            fontWeight: FontWeight.bold),
                      ),
                    ),
                    Container(
                      child: Slider.adaptive(
                        value: prizeMoney.toDouble(),
                        max: 10000,
                        divisions: 100,
                        label: "\$ $prizeMoney",
                        onChanged: (val) {
                          setState(() {
                            prizeMoney = val.toInt();
                          });
                        },
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          Container(
            width: double.infinity,
            height: 50,
            child: TextButton(
              child: Text(
                AppLocalizations.of(context)!.startHunt,
                style: BLTFonts.system(
                  textStyle: TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                  ),
                ),
              ),
              style: ButtonStyle(
                shape: WidgetStateProperty.all<RoundedRectangleBorder>(
                  RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8.0),
                  ),
                ),
                backgroundColor: WidgetStateProperty.all(
                  isDarkMode
                      ? BLTColors.primaryDark
                      : BLTColors.primary,
                ),
              ),
              onPressed: () {},
            ),
          ),
          SizedBox(
            height: 20.0,
          ),
        ],
      ),
    );
  }
}
