// import 'dart:convert';
import 'dart:io';
import 'dart:ui';

import 'package:bugheist/global/variables.dart';
import 'package:bugheist/pages/home/start_hunt.dart';
import 'package:bugheist/providers/login_provider.dart';
import 'package:bugheist/util/api/issues_api.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';

import '../../models/issue_model.dart';
import '../../util/enums/login_type.dart';

class ReportBug extends ConsumerStatefulWidget {
  const ReportBug({Key? key}) : super(key: key);

  @override
  ConsumerState<ConsumerStatefulWidget> createState() => _ReportBugState();
}

class _ReportBugState extends ConsumerState<ReportBug> {
  String selectedWidgetName = "Report Issue";

  Widget bodyWidget = SizedBox();

  List<DropdownMenuItem<String>> _dropDownItem() {
    List<String> ddl = [
      "Report Issue",
      "Start Bug Hunt",
    ];
    return ddl.map(
      (value) {
        return DropdownMenuItem(
          value: value,
          child: Text(
            value,
            style: GoogleFonts.ubuntu(
              textStyle: TextStyle(color: Color(0xFF737373), fontSize: 30),
            ),
          ),
        );
      },
    ).toList();
  }

  buildPageSwitcher(Size size) {
    LoginType loginType = ref.watch(loginProvider.notifier).loginType;

    return (loginType == LoginType.guest)
        ? Container(
            padding: EdgeInsets.fromLTRB(0, 12, 0, 0),
            alignment: Alignment.centerLeft,
            child: Text(
              "Report Issue",
              style: GoogleFonts.ubuntu(
                textStyle: TextStyle(color: Color(0xFF737373), fontSize: 30),
              ),
            ),
          )
        : DropdownButton(
            items: _dropDownItem(),
            value: selectedWidgetName,
            onChanged: (val) {
              selectedWidgetName = val.toString();
              switch (val) {
                case "Report Issue":
                  setState(() {
                    bodyWidget = ReportForm(
                      size: size,
                      parentContext: context,
                    );
                  });
                  break;
                case "Start Bug Hunt":
                  setState(() {
                    bodyWidget = StartHuntPage();
                  });
                  break;
                default:
                  setState(() {
                    bodyWidget = ReportForm(
                      size: size,
                      parentContext: context,
                    );
                  });
              }
            },
          );
  }

  @override
  void initState() {
    super.initState();
    bodyWidget = ReportForm(
      size: window.physicalSize / window.devicePixelRatio,
      parentContext: context,
    );
  }

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          buildPageSwitcher(size),
          bodyWidget,
        ],
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
    final imageFile = await picker.getImage(source: ImageSource.gallery);
    if (imageFile != null) {
      var image = File(imageFile.path);
      setState(() {
        _image = image;
      });
      // WidgetsBinding.instance.addPostFrameCallback((timeStamp) => setState(() {
      //       _image = image;
      //     }));
    } else {
      print('No image selected.');
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
              ],
            ),
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
                LoginType loginType =
                    ref.watch(loginProvider.notifier).loginType;
                if (loginType == LoginType.user) {
                  if (_formKey.currentState!.validate()) {
                    if (_image != null) {
                      Issue issue = Issue(
                        user: currentUser!,
                        url: _titleController.text,
                        description: _descriptionController.text,
                        isVerified: false,
                        isOpen: false,
                        ocr: _image!.path,
                      );
                      await IssueApiClient.postIssue(
                          issue, widget.parentContext);
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
                } else {
                  SnackBar cantSnak = SnackBar(
                    content: Text("You need to login to report issues!"),
                  );
                  ScaffoldMessenger.of(widget.parentContext).showSnackBar(
                    cantSnak,
                  );
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
