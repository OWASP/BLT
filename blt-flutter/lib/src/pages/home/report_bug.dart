import 'dart:io';
import 'dart:typed_data';
import 'dart:ui';

import 'package:blt/src/util/api/general_api.dart';
import 'package:blt/src/util/endpoints/general_endpoints.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:pasteboard/pasteboard.dart';
import 'package:path_provider/path_provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../global/variables.dart';
import '../../util/api/issues_api.dart';
import '../../models/issue_model.dart';

/// Report Bug and Start Bug Hunt Page, namesake, used for
/// posting bugs, companies and individuals
/// should be able to start bughunts.
class ReportBug extends ConsumerStatefulWidget {
  const ReportBug({Key? key}) : super(key: key);
  @override
  ConsumerState<ConsumerStatefulWidget> createState() => _ReportBugState();
}

class _ReportBugState extends ConsumerState<ReportBug> {

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(horizontal: 20),
      child: ReportForm(
        size: window.physicalSize / window.devicePixelRatio,
        parentContext: context,
      ),
    );
  }
}

class ReportForm extends ConsumerStatefulWidget {
  final Size size;
  final BuildContext parentContext;

  const ReportForm({
    Key? key,
    required this.size,
    required this.parentContext,
  }) : super(key: key);

  @override
  ConsumerState<ConsumerStatefulWidget> createState() => _ReportFormState();
}

class _ReportFormState extends ConsumerState<ReportForm> {
  final _descriptionController = TextEditingController();
  final _titleController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  File? _image;
  final picker = ImagePicker();

  Future<void> _pickImageFromGallery() async {
    final imageFile = await picker.pickImage(source: ImageSource.gallery);
    if (imageFile != null) {
      var image = File(imageFile.path);
      setState(() {
        _image = image;
      });
    } else {
      print('No image selected.');
    }
  }

  Future<File> _coverToImage(Uint8List imageBytes) async {
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
        image = await _coverToImage(imageBytes);
      }
      setState(() {
        _image = image;
      });
    } catch (e) {
      print('No Image Found On Clipboard');
    }
  }

  void showDuplicateDialog(BuildContext context) {
    if (_titleController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("URL field is required"),
        ),
      );
      return;
    }
    showGeneralDialog(
      context: context,
      barrierLabel: "Barrier",
      barrierDismissible: true,
      barrierColor: Colors.black.withOpacity(0.5),
      transitionDuration: Duration(milliseconds: 400),
      pageBuilder: (_, __, ___) {
        return FutureBuilder<Map<String, String>?>(
          future: GeneralApiClient.checkForDuplicate(_titleController.text),
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.done) {
              Map<String, String>? m = snapshot.data;
              if (m == null) {
                return AlertDialog(
                  title: Text(
                    'Sweet!',
                    style: GoogleFonts.ubuntu(
                      textStyle: TextStyle(
                        color: Color(0xFFDC4654),
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  content: Text(
                    "We haven't got any bug from this URL till now.",
                    style: GoogleFonts.aBeeZee(
                      textStyle: TextStyle(
                        color: Color(0xFF737373),
                      ),
                    ),
                  ),
                );
              } else {
                return AlertDialog(
                  title: Text(
                    'A bug with same URL already exists!',
                    style: GoogleFonts.ubuntu(
                      textStyle: TextStyle(
                        color: Color(0xFFDC4654),
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  content: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      RichText(
                        text: TextSpan(
                          style: GoogleFonts.aBeeZee(
                            textStyle: TextStyle(
                              color: Color(0xFF737373),
                            ),
                          ),
                          children: <TextSpan>[
                            TextSpan(
                              text: "Description: ",
                              style: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  color: Color(0xFF737373),
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                            TextSpan(text: m["description"])
                          ],
                        ),
                      ),
                      SizedBox(
                        height: 16.0,
                      ),
                      RichText(
                        text: TextSpan(
                          style: GoogleFonts.aBeeZee(
                            textStyle: TextStyle(
                              color: Color(0xFF737373),
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          children: <TextSpan>[
                            TextSpan(
                              text:
                                  "Ensure you are not submitting a duplicate bug by checking here: ",
                            ),
                            TextSpan(
                              text:
                                  "${GeneralEndPoints.domain}issue/${m["id"]}",
                              style: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  color: Color(0xFF4A93F8),
                                  decoration: TextDecoration.underline,
                                ),
                              ),
                              recognizer: TapGestureRecognizer()
                                ..onTap = () async {
                                  Uri site = Uri.parse(
                                      "${GeneralEndPoints.baseUrl}issue/${m["id"]}");
                                  try {
                                    await launchUrl(site,
                                        mode: LaunchMode.externalApplication);
                                  } catch (e) {}
                                },
                            )
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }
            }
            return Center(
              child: CircularProgressIndicator(),
            );
          },
        );
      },
      transitionBuilder: (_, anim, __, child) {
        Tween<Offset> tween;
        if (anim.status == AnimationStatus.reverse) {
          tween = Tween(begin: Offset(-1, 0), end: Offset.zero);
        } else {
          tween = Tween(begin: Offset(1, 0), end: Offset.zero);
        }

        return SlideTransition(
          position: tween.animate(anim),
          child: FadeTransition(
            opacity: anim,
            child: child,
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final Size size = widget.size;
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: EdgeInsets.fromLTRB(0, 12, 0, 0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "App name/ url",
                  style: GoogleFonts.ubuntu(
                    textStyle: TextStyle(
                      color: Color(0xFFDC4654),
                      fontSize: 15,
                    ),
                  ),
                ),
                SizedBox(
                  height: 12,
                ),
                SizedBox(
                  height: 40,
                  child: TextFormField(
                    controller: _titleController,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return "This field is required";
                      }
                      return null;
                    },
                    decoration: InputDecoration(
                      hintText: "Enter the URL or app name of the issue ...",
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
                Builder(builder: (context) {
                  return TextButton(
                    onPressed: () {
                      showDuplicateDialog(context);
                    },
                    child: Text(
                      "Check for duplicates",
                      style: GoogleFonts.ubuntu(
                        textStyle: TextStyle(
                          color: Color(0xFFDC4654),
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  );
                }),
              ],
            ),
          ),
          SizedBox(
            height: 12,
          ),
          Container(
            padding: EdgeInsets.fromLTRB(0, 12, 0, 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "Description",
                  style: GoogleFonts.ubuntu(
                    textStyle: TextStyle(
                      color: Color(0xFFDC4654),
                      fontSize: 15,
                    ),
                  ),
                ),
                SizedBox(
                  height: 12,
                ),
                SizedBox(
                  height: 80,
                  child: TextFormField(
                    controller: _descriptionController,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return "This field is required";
                      }
                      return null;
                    },
                    maxLines: 5,
                    decoration: InputDecoration(
                      hintText: "Enter a description of the issue here ...",
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.all(Radius.circular(10.0)),
                        borderSide: BorderSide(color: Colors.grey),
                      ),
                    ),
                    style: GoogleFonts.aBeeZee(
                      textStyle: TextStyle(
                        fontSize: 12,
                      ),
                    ),
                    cursorColor: Color(0xFFDC4654),
                  ),
                ),
              ],
            ),
          ),
          Row(
            children: [
              SizedBox(
                child: TextButton(
                  child: Text(
                    "Choose Image",
                    style: GoogleFonts.ubuntu(
                      textStyle: TextStyle(
                        color: Colors.white,
                        fontSize: 15,
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
                        fontSize: 15,
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
          Container(
            height: 280,
            width: size.width,
            child: _image == null
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
                    _image!,
                    fit: BoxFit.cover,
                  ),
            decoration: BoxDecoration(
              border: _image != null
                  ? Border.all(
                      color: Color(0xFFDC4654),
                      width: 0.5,
                    )
                  : null,
              borderRadius: _image != null ? BorderRadius.circular(15) : null,
            ),
          ),
          Padding(
            padding: EdgeInsets.fromLTRB(0, 10, 0, 10),
            child: Text(
              "Note: Adding an issue gives you 3 points!",
              style: GoogleFonts.aBeeZee(
                textStyle: TextStyle(
                  color: Color(0xFF737373),
                  fontSize: 12,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ),
          ),
          Container(
            width: size.width,
            height: 50,
            child: TextButton(
              child: Text(
                "Add Issue",
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
              onPressed: () async {
                if (_formKey.currentState!.validate()) {
                  if (_image != null) {
                    Issue issue = Issue(
                      user: currentUser!,
                      url: _titleController.text,
                      description: _descriptionController.text,
                      isVerified: false,
                      isOpen: true,
                      ocr: _image!.path,
                      userAgent:
                          "Dart ${Platform.version.substring(0, 7) + Platform.operatingSystem}",
                    );
                    await IssueApiClient.postIssue(issue, widget.parentContext);
                  } else {
                    SnackBar cantSnak = SnackBar(
                      content:
                          Text("You need to upload a screenshot of issue!"),
                    );
                    ScaffoldMessenger.of(widget.parentContext).showSnackBar(
                      cantSnak,
                    );
                  }
                }
              },
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
