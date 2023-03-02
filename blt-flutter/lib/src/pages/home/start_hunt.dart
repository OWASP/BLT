import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:pasteboard/pasteboard.dart';
import 'package:path_provider/path_provider.dart';

/// Sub page which adds "start bug hunt" functionality to the Report Bug page.
class StartHuntPage extends StatefulWidget {
  const StartHuntPage({Key? key}) : super(key: key);

  @override
  State<StartHuntPage> createState() => _StartHuntPageState();
}

class _StartHuntPageState extends State<StartHuntPage> {
  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return HuntForm(
      size: size,
    );
  }
}

class HuntForm extends StatefulWidget {
  final Size size;
  const HuntForm({Key? key, required this.size}) : super(key: key);

  @override
  State<HuntForm> createState() => _HuntFormState();
}

class _HuntFormState extends State<HuntForm> {
  late TextEditingController _websiteController;
  File _image = File("");
  final picker = ImagePicker();
  int prizeMoney = 100;

  Future _pickImageFromGallery() async {
    final imageFile = await picker.pickImage(source: ImageSource.gallery);

    setState(() {
      if (imageFile != null) {
        _image = File(imageFile.path);
      } else {
        print('No image selected.');
      }
    });
  }

    Future<File> _convertToImage(Uint8List imageBytes) async{
    String tempPath = (await getTemporaryDirectory()).path;
    File file = File('$tempPath/profile.png');
    await file.writeAsBytes(
      imageBytes.buffer.asUint8List(imageBytes.offsetInBytes, imageBytes.lengthInBytes));
    return file;
  }

  Future<void> _pasteImageFromClipBoard() async{
    try {
    final imageBytes = await Pasteboard.image;
    late File? image ;
    if(imageBytes != null){
     image = await _convertToImage(imageBytes);
    }
    setState(() {
      _image = image! ;
    });
    }
    catch(e){
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
    final Size size = widget.size;
    return Form(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 12.0),
            child: Text(
              "App name/ url",
              style: GoogleFonts.ubuntu(
                textStyle: TextStyle(
                  color: Color(0xFFDC4654),
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
                hintText: "Enter the URL or app name for the hunt ...",
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
              cursorColor: Color(0xFFDC4654),
              style: GoogleFonts.aBeeZee(
                textStyle: TextStyle(
                  fontSize: 12,
                ),
              ),
            ),
          ),
          Container(
            margin: const EdgeInsets.symmetric(vertical: 8.0),
            child:Row(
              children: [
              SizedBox(
                child: TextButton(
                  child: Text(
                    "Choose Image",
                    style: GoogleFonts.ubuntu(
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
                    backgroundColor: MaterialStateProperty.all(
                      Color(0xFFDC4654),
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
                    "Choose From Clipboard",
                    style: GoogleFonts.ubuntu(
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
                    backgroundColor: MaterialStateProperty.all(
                      Color(0xFFDC4654),
                    ),
                  ),
                ),
              ),
            ],
          ),
          ),
          Container(
            height: 280,
            width: size.width,
            margin: const EdgeInsets.only(bottom: 12.0),
            child: _image.path == ""
                ? Center(
                    child: Text(
                      'No image selected.',
                      style: GoogleFonts.aBeeZee(
                        textStyle: TextStyle(
                          color: Color(0xFF737373),
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
                      color: Color(0xFFDC4654),
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
                  "Set Prize Money",
                  style: GoogleFonts.ubuntu(
                    textStyle: TextStyle(
                      color: Color(0xFFDC4654),
                      fontSize: 20,
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8.0),
                  child: Text(
                    "This amount will be rewarded to the users who hunt bugs succesfully for your app/website",
                    style: GoogleFonts.aBeeZee(
                      textStyle: TextStyle(
                        color: Color(0xFF737373),
                      ),
                    ),
                  ),
                ),
                Row(
                  children: [
                    Text(
                      "\$ $prizeMoney",
                      style: GoogleFonts.ubuntu(
                        textStyle: TextStyle(
                            color: Color(0xFFDC4654),
                            fontWeight: FontWeight.bold),
                      ),
                    ),
                    Container(
                      width: 0.6 * size.width,
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
            width: size.width,
            height: 50,
            child: TextButton(
              child: Text(
                "Start Hunt!",
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                  ),
                ),
              ),
              style: ButtonStyle(
                shape: MaterialStateProperty.all<RoundedRectangleBorder>(
                  RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8.0),
                  ),
                ),
                backgroundColor: MaterialStateProperty.all(
                  Color(0xFFDC4654),
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
