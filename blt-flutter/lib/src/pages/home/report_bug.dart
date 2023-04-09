import 'dart:io';
import 'dart:math';
//import 'dart:typed_data';
import 'dart:ui';

import 'package:blt/src/util/api/general_api.dart';
import 'package:blt/src/util/endpoints/general_endpoints.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
//import 'package:pasteboard/pasteboard.dart';
//import 'package:path_provider/path_provider.dart';
import 'package:receive_sharing_intent/receive_sharing_intent.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../../global/variables.dart';
import '../../util/api/issues_api.dart';
import '../../models/issue_model.dart';

/// Report Bug and Start Bug Hunt Page, namesake, used for
/// posting bugs, companies and individuals
/// should be able to start bughunts.
class ReportBug extends ConsumerStatefulWidget {
  final ReportPageDefaults reportPageDefaults;
  const ReportBug({Key? key, required this.reportPageDefaults})
      : super(key: key);
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
        reportPageDefaults: widget.reportPageDefaults,
      ),
    );
  }
}

class ReportForm extends ConsumerStatefulWidget {
  final Size size;
  final BuildContext parentContext;
  final ReportPageDefaults reportPageDefaults;

  const ReportForm({
    Key? key,
    required this.size,
    required this.parentContext,
    required this.reportPageDefaults,
  }) : super(key: key);

  @override
  ConsumerState<ConsumerStatefulWidget> createState() => _ReportFormState();
}

class _ReportFormState extends ConsumerState<ReportForm> {
  final _descriptionController = TextEditingController();
  final _titleController = TextEditingController();
  int _selectedIssueCategoriesIndex = 0;
  ValueNotifier<int> _selectedDescriptionLabelIndex = ValueNotifier(0);
  bool duplicateVerified = false;
  final _formKey = GlobalKey<FormState>();
  List<File> _image = [];
  final picker = ImagePicker();
  List<String> _issueCategories = [
    "General",
    "Number error",
    "Functional",
    "Performance",
    "Security",
    "Typo",
    "Design",
    "Server down"
  ];

  Future<void> _pickImageFromGallery() async {
    final imageFile = await picker.pickMultiImage();
    if (!imageFile.isEmpty) {
      var imgs = _image;
      for (var img in imageFile) {
        if (imgs.length == 5) break;
        imgs.add(File(img.path));
      }
      setState(() {
        _image = imgs;
      });
    }
  }

  // Future<File> _coverToImage(Uint8List imageBytes) async {
  //   String tempPath = (await getTemporaryDirectory()).path;
  //   File file = File('$tempPath/profile.png');
  //   await file.writeAsBytes(imageBytes.buffer
  //       .asUint8List(imageBytes.offsetInBytes, imageBytes.lengthInBytes));
  //   return file;
  // }

  // Future<void> _pasteImageFromClipBoard() async {
  //   try {
  //     final imageBytes = await Pasteboard.image;
  //     late File? image;
  //     if (imageBytes != null) {
  //       image = await _coverToImage(imageBytes);
  //     }
  //     setState(() {
  //       _image = image;
  //     });
  //   } catch (e) {
  //     print('No Image Found On Clipboard');
  //   }
  // }

  void showIssueCategories(BuildContext context) {
    showModalBottomSheet(
        context: context,
        builder: (context) {
          return Container(
            padding: EdgeInsets.fromLTRB(0, 20, 0, 0),
            child: ListView.builder(
                itemCount: 8,
                itemBuilder: (BuildContext context, index) {
                  return ListTile(
                    onTap: () {
                      setState(() {
                        _selectedIssueCategoriesIndex = index;
                      });
                      Navigator.of(context).pop();
                    },
                    title: Text(
                      _issueCategories[index],
                      style: GoogleFonts.ubuntu(
                        textStyle: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  );
                }),
          );
        },
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(25.0),
          ),
        ));
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

              duplicateVerified = true;
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
  void initState() {
    super.initState();
    if (widget.reportPageDefaults.sharedMediaFile != null) {
      _image = [File(widget.reportPageDefaults.sharedMediaFile!.path)];
    }
    if (widget.reportPageDefaults.text != null) {
      _titleController.text = widget.reportPageDefaults.text!;
    }
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
                  "Report issue",
                  style: GoogleFonts.ubuntu(
                    textStyle: TextStyle(
                      color: Color(0xFFDC4654),
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                SizedBox(
                  height: 32,
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
                    onChanged: (v) {
                      if (duplicateVerified) {
                        setState(() {
                          duplicateVerified = false;
                        });
                      }
                    },
                    decoration: InputDecoration(
                      hintText: "App name / URL",
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
                      contentPadding:
                          EdgeInsets.only(top: 8.0, left: 16.0, right: 16.0),
                    ),
                    cursorColor: Color(0xFFDC4654),
                    style: GoogleFonts.aBeeZee(
                      textStyle: TextStyle(
                        fontSize: 12,
                      ),
                    ),
                  ),
                ),
                SizedBox(
                  height: 16.0,
                ),
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        height: 40,
                        decoration: BoxDecoration(
                          border: Border.all(color: Colors.grey),
                          borderRadius: BorderRadius.all(
                            Radius.circular(8),
                          ),
                        ),
                        child: Row(
                          children: [
                            SizedBox(
                              width: 16.0,
                            ),
                            Text(
                              _issueCategories[_selectedIssueCategoriesIndex],
                              style: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  fontSize: 12,
                                ),
                              ),
                            ),
                            Spacer(),
                            Container(
                              height: 27.0,
                              width: 27.0,
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.all(
                                  Radius.circular(8),
                                ),
                                color: Color(0xFFDC4654),
                              ),
                              child: Center(
                                child: Builder(builder: (context) {
                                  return IconButton(
                                    padding: EdgeInsets.zero,
                                    onPressed: () {
                                      showIssueCategories(context);
                                    },
                                    icon: Icon(
                                      Icons.keyboard_arrow_down,
                                      color: Colors.white,
                                      size: 20.0,
                                    ),
                                  );
                                }),
                              ),
                            ),
                            SizedBox(
                              width: 6.5,
                            ),
                          ],
                        ),
                      ),
                    ),
                    SizedBox(
                      width: 16.0,
                    ),
                    Expanded(
                      child: Container(
                        height: 40,
                        child: Builder(builder: (context) {
                          return TextButton(
                            child: Text(
                              "Check for Duplicates",
                              style: GoogleFonts.ubuntu(
                                textStyle: TextStyle(
                                  color: Colors.white,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                            style: ButtonStyle(
                              shape: MaterialStateProperty.all<
                                  RoundedRectangleBorder>(
                                RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(8.0),
                                ),
                              ),
                              backgroundColor: MaterialStateProperty.all(
                                duplicateVerified
                                    ? Color(0xFF50C878)
                                    : Color(0xFFDC4654),
                              ),
                            ),
                            onPressed: () async {
                              showDuplicateDialog(context);
                              setState(() {
                                duplicateVerified = true;
                              });
                            },
                          );
                        }),
                      ),
                    ),
                  ],
                ),
                SizedBox(
                  height: 16.0,
                ),
                Container(
                  height: 225.0,
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.grey),
                    borderRadius: BorderRadius.all(
                      Radius.circular(8),
                    ),
                  ),
                  child: Column(
                    children: [
                      Expanded(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16.0),
                          child: ValueListenableBuilder(
                            valueListenable: _selectedDescriptionLabelIndex,
                            builder: (context, value, widget) {
                              if (value == 0) {
                                return TextFormField(
                                  controller: _descriptionController,
                                  validator: (value) {
                                    if (value == null || value.isEmpty) {
                                      return "This field is required";
                                    }
                                    return null;
                                  },
                                  keyboardType: TextInputType.multiline,
                                  maxLines: null,
                                  decoration: InputDecoration(
                                    hintText: "Description",
                                    border: InputBorder.none,
                                  ),
                                  style: GoogleFonts.aBeeZee(
                                    textStyle: TextStyle(
                                      fontSize: 12,
                                    ),
                                  ),
                                  cursorColor: Color(0xFFDC4654),
                                );
                              }
                              return Container(
                                child: Markdown(
                                  padding: EdgeInsets.symmetric(vertical: 16.0),
                                  data: _descriptionController.text,
                                  styleSheet: MarkdownStyleSheet.fromTheme(
                                    ThemeData(
                                      fontFamily:
                                          GoogleFonts.aBeeZee().fontFamily,
                                      textTheme: TextTheme(
                                        bodyMedium: GoogleFonts.aBeeZee(
                                          textStyle: TextStyle(
                                            fontSize: 12,
                                            color: Color(0xFF737373),
                                          ),
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                      ),
                      Container(
                        height: 1,
                        color: Colors.grey,
                      ),
                      Container(
                        height: 40.0,
                        child: Row(
                          children: [
                            Expanded(
                              child: Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceEvenly,
                                children: [
                                  IconButton(
                                    padding: EdgeInsets.zero,
                                    constraints: BoxConstraints(),
                                    onPressed: () {},
                                    icon: SvgPicture.asset(
                                      "assets/input_bold.svg",
                                      width: 15.0,
                                    ),
                                  ),
                                  IconButton(
                                    padding: EdgeInsets.zero,
                                    constraints: BoxConstraints(),
                                    onPressed: () {},
                                    icon: SvgPicture.asset(
                                      "assets/input_italic.svg",
                                      height: 16.0,
                                    ),
                                  ),
                                  IconButton(
                                    padding: EdgeInsets.zero,
                                    constraints: BoxConstraints(),
                                    onPressed: () {},
                                    icon: SvgPicture.asset(
                                      "assets/input_link.svg",
                                      height: 15.0,
                                    ),
                                  ),
                                  IconButton(
                                    padding: EdgeInsets.zero,
                                    constraints: BoxConstraints(),
                                    onPressed: () {},
                                    icon: SvgPicture.asset(
                                      "assets/input_image.svg",
                                      height: 15.0,
                                    ),
                                  ),
                                  IconButton(
                                    padding: EdgeInsets.zero,
                                    constraints: BoxConstraints(),
                                    onPressed: () {},
                                    icon: SvgPicture.asset(
                                      "assets/input_list.svg",
                                      height: 15.0,
                                    ),
                                  ),
                                  IconButton(
                                    padding: EdgeInsets.zero,
                                    constraints: BoxConstraints(),
                                    onPressed: () {},
                                    icon: SvgPicture.asset(
                                      "assets/input_task.svg",
                                      height: 15.0,
                                    ),
                                  ),
                                  IconButton(
                                    padding: EdgeInsets.zero,
                                    constraints: BoxConstraints(),
                                    onPressed: () {},
                                    icon: SvgPicture.asset(
                                      "assets/input_heading.svg",
                                      height: 15.0,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Container(
                              width: 1.0,
                              color: Colors.grey,
                            ),
                            InkWell(
                              onTap: () {
                                setState(() {
                                  _selectedDescriptionLabelIndex.value =
                                      1 - _selectedDescriptionLabelIndex.value;
                                });
                              },
                              child: Ink(
                                child: Container(
                                  width: 100,
                                  child: Center(
                                    child: Text(
                                      _selectedDescriptionLabelIndex.value == 1
                                          ? "Edit"
                                          : "Preview",
                                      style: GoogleFonts.ubuntu(
                                        textStyle: TextStyle(
                                          color: Color(0xFFDC4654),
                                          fontSize: 13,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.only(top: 16.0),
                  child: SizedBox(
                    height: 125.0,
                    child: ListView.builder(
                      scrollDirection: Axis.horizontal,
                      itemCount: min(5, _image.length + 1),
                      itemBuilder: (_, i) {
                        if (i < _image.length) {
                          return Container(
                            width: 125.0,
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.all(
                                Radius.circular(8),
                              ),
                            ),
                            child: Card(
                              elevation: 1,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Stack(
                                children: [
                                  ClipRRect(
                                    borderRadius: BorderRadius.circular(8.0),
                                    child: Image.file(
                                      _image[i],
                                      fit: BoxFit.cover,
                                      width: double.infinity,
                                      height: double.infinity,
                                    ),
                                  ),
                                  Padding(
                                    padding: const EdgeInsets.all(8.0),
                                    child: Container(
                                      width: 30.0,
                                      height: 30.0,
                                      decoration: BoxDecoration(
                                        borderRadius: BorderRadius.all(
                                          Radius.circular(15),
                                        ),
                                        color: Color(0xFFDC4654),
                                      ),
                                      child: IconButton(
                                        padding: EdgeInsets.zero,
                                        onPressed: () {
                                          setState(() {
                                            _image.removeAt(i);
                                          });
                                        },
                                        icon: Icon(
                                          Icons.close,
                                          color: Colors.white,
                                          size: 20.0,
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        } else {
                          return SizedBox(
                            width: 125.0,
                            child: Card(
                              elevation: 1,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: InkWell(
                                onTap: () {
                                  _pickImageFromGallery();
                                },
                                child: Ink(
                                  child: Container(
                                    height: 280.0,
                                    decoration: BoxDecoration(
                                      borderRadius: BorderRadius.all(
                                        Radius.circular(8),
                                      ),
                                      color: Color(0xFFF8D2CD),
                                    ),
                                    child: Center(
                                      child: Column(
                                        children: [
                                          Spacer(),
                                          SvgPicture.asset(
                                            "assets/select_image.svg",
                                            width: 45.0,
                                          ),
                                          SizedBox(
                                            height: 16.0,
                                          ),
                                          Text(
                                            "Add images",
                                            style: GoogleFonts.ubuntu(
                                              textStyle: TextStyle(
                                                color: Color(0xFFDC4654),
                                                fontSize: 12,
                                                fontWeight: FontWeight.bold,
                                              ),
                                            ),
                                          ),
                                          Spacer(),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          );
                        }
                      },
                    ),
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: EdgeInsets.fromLTRB(0, 16, 0, 16),
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
                  if (_image.isNotEmpty) {
                    Issue issue = Issue(
                      user: currentUser!,
                      url: _titleController.text,
                      description: _descriptionController.text,
                      isVerified: false,
                      isOpen: true,
                      screenshotsLink: _image.map((e) => e.path).toList(),
                      userAgent:
                          "Dart ${Platform.version.substring(0, 7) + Platform.operatingSystem}",
                      label: _selectedIssueCategoriesIndex,
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

class ReportPageDefaults {
  final SharedMediaFile? sharedMediaFile;
  final String? text;

  ReportPageDefaults({this.sharedMediaFile, this.text});
}
