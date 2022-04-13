import 'dart:io';

//import 'package:../state_container.dart';
import 'package:flutter/material.dart';
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
    return SingleChildScrollView(
      child: Column(
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.all(20.0),
            child: TextField(
              controller: _messageTitleTextController,
              decoration: InputDecoration(
                hintText: "Enter the URL or app name of the issue",
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.all(Radius.circular(10.0)),
                  borderSide: BorderSide(color: Colors.grey),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.all(Radius.circular(10.0)),
                  borderSide: BorderSide(color: Colors.grey),
                ),
              ),
              onChanged: (String value) {
                setState(() {
                  _messageValue = value;
                });
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20.0),
            child: TextField(
              controller: _messageTextController,
              maxLines: 5,
              decoration: InputDecoration(
                hintText: "Enter a description of the issue here",
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.all(Radius.circular(10.0)),
                  borderSide: BorderSide(color: Colors.grey),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.all(Radius.circular(10.0)),
                  borderSide: BorderSide(color: Colors.grey),
                ),
              ),
              onChanged: (String value) {
                setState(() {
                  _messageValue = value;
                });
              },
            ),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              SizedBox(
                child: ElevatedButton(
                  child: Text("Choose Image"),
                  onPressed: () {
                    _pickImageFromGallery();
                    setState(() {
                      _messageTextController.text = _messageValue;
                    });
                  },
                ),
              ),
              SizedBox(
                width: 20.0,
              ),
              SizedBox(
                child: ElevatedButton(
                  child: Text("Add Issue +3pts"),
                  onPressed: () {
                    uploadBtnPress();
                  },
                ),
              ),
            ],
          ),
          SizedBox(
            height: 20.0,
          ),
          SizedBox(
            height: 200,
            child: Center(
              child: _image.path == ""
                  ? Text('No image selected.')
                  : Image.file(_image),
            ),
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
