import 'dart:io';

//import 'package:../state_container.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';

//import '../services/api.dart';

class ReportBug extends StatefulWidget {
  const ReportBug({Key? key}) : super(key: key);

  @override
  _ReportBugState createState() => _ReportBugState();
}

class _ReportBugState extends State<ReportBug> {
  final _messageTextController = TextEditingController();
  final _messageTitleTextController = TextEditingController();
  String _messageValue = '';
  late String token;

  File _image = File("");

  bool isLoading = false;
  bool isButtonDisable = false;
  final picker = ImagePicker();

  Future _pickImageFromGallery() async {
    final imageFile = await picker.getImage(source: ImageSource.gallery);

    setState(() {
      if (imageFile != null) {
        _image = File(imageFile.path);
      } else {
        print('No image selected.');
      }
    });
  }

  Future<void> _showThankYouDialog(BuildContext context) {
    return showDialog<void>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text('Thank you for reporting an issue.'),
          actions: <Widget>[
            TextButton(
              child: Text('Ok'),
              onPressed: () {
                _messageTextController.clear();
                setState(() {
                  _messageValue = _messageTextController.text;
                  //_image = null;
                  //file = null;
                });
                Navigator.of(context).pop();
              },
            ),
          ],
        );
      },
    );
  }

  @override
  void initState() {
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            padding: EdgeInsets.fromLTRB(0, 12, 0, 0),
            alignment: Alignment.centerLeft,
            child: Text(
              "Report Issue",
              style: GoogleFonts.ubuntu(
                textStyle: TextStyle(color: Color(0xFF737373), fontSize: 30),
              ),
            ),
          ),
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
                  child: TextField(
                    controller: _messageTitleTextController,
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
                        color: Colors.white,
                        fontSize: 12,
                      ),
                    ),
                    onChanged: (String value) {
                      setState(() {
                        _messageValue = value;
                      });
                    },
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
                  child: TextField(
                    controller: _messageTextController,
                    maxLines: 5,
                    decoration: InputDecoration(
                      hintText: "Enter a description of the issue here ...",
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.all(Radius.circular(10.0)),
                        borderSide: BorderSide(color: Colors.grey),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.all(Radius.circular(10.0)),
                        borderSide: BorderSide(color: Colors.grey),
                      ),
                    ),
                    style: GoogleFonts.aBeeZee(
                      textStyle: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                      ),
                    ),
                    onChanged: (String value) {
                      setState(() {
                        _messageValue = value;
                      });
                    },
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
                setState(() {
                  _messageTextController.text = _messageValue;
                });
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
              onPressed: () {
                uploadBtnPress();
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

  Function? uploadBtnPress() {
    if (isButtonDisable) {
      return null;
    } else {
      print('return upload issue');
      uploadIssue();
      return null;
    }
  }

  void uploadIssue() async {
    if (_image.path != "") {
      setState(() {
        isLoading = true;
        isButtonDisable = true;
      });
      // await RestDatasource().reportIssue(
      //     _image, _messageValue, StateContainer.of(context).loggedInUser.token);

      _showThankYouDialog(context);

      setState(() {
        isLoading = false;
        isButtonDisable = false;
      });
    }
  }
}
