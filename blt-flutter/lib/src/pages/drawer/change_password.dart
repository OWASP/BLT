import '../pages_import.dart';

/// The change password page for the app.
class ChangePasswordPage extends StatefulWidget {
  const ChangePasswordPage({Key? key}) : super(key: key);

  @override
  State<ChangePasswordPage> createState() => _ChangePasswordPageState();
}

class _ChangePasswordPageState extends State<ChangePasswordPage> {
  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Icon(
            Icons.arrow_back_ios_new_rounded,
            color: Colors.white,
          ),
          onPressed: () {
            Navigator.of(context).pop();
          },
        ),
      ),
      backgroundColor: Colors.transparent,
      extendBodyBehindAppBar: true,
      body: Stack(
        children: [
          Container(
            width: size.width,
            height: size.height,
            color: Color(0xFFDC4654),
            child: Column(
              children: [
                SizedBox(
                  width: size.width,
                  height: size.height * 0.35,
                  child: Padding(
                    padding: EdgeInsets.symmetric(
                      horizontal: 0.125 * size.width,
                      vertical: 0.085 * size.height,
                    ),
                    child: Center(
                      child: SvgPicture.asset(
                        'assets/logo_white.svg',
                        fit: BoxFit.contain,
                        height: 192.0,
                      ),
                    ),
                  ),
                ),
                SizedBox(
                  width: size.width,
                  height: size.height * 0.65,
                ),
              ],
            ),
          ),
          Positioned(
            bottom: 0,
            child: Container(
              width: size.width,
              height: size.height * 0.65,
              decoration: BoxDecoration(
                color: Theme.of(context).canvasColor,
                boxShadow: [
                  BoxShadow(
                    spreadRadius: 10,
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 50,
                  )
                ],
                borderRadius: BorderRadius.only(
                  topLeft: Radius.circular(50),
                  topRight: Radius.circular(50.0),
                ),
              ),
              child: Center(
                child: ChangePasswordForm(
                  size: size,
                ),
              ),
            ),
          )
        ],
      ),
    );
  }
}

class ChangePasswordForm extends StatefulWidget {
  final Size size;
  const ChangePasswordForm({
    Key? key,
    required this.size,
  }) : super(key: key);

  @override
  State<ChangePasswordForm> createState() => _ChangePasswordFormState();
}

class _ChangePasswordFormState extends State<ChangePasswordForm> {
  final _formKey = GlobalKey<FormState>();

  late TextEditingController _oldController, _new1Controller, _new2Controller;

  @override
  void initState() {
    super.initState();
    _oldController = TextEditingController();
    _new1Controller = TextEditingController();
    _new2Controller = TextEditingController();
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(
            width: 0.8 * widget.size.width,
            child: TextFormField(
              controller: _oldController,
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return AppLocalizations.of(context)!.requiredField;
                }
                return null;
              },
              onChanged: (val) {},
              decoration: InputDecoration(
                hintText: AppLocalizations.of(context)!.oldPassword,
                prefixIcon: Icon(Icons.key_rounded),
                filled: true,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10.0),
                  borderSide: BorderSide(
                    color: Color(0xFF737373),
                  ),
                ),
                fillColor: Colors.white.withOpacity(0.35),
              ),
              obscureText: true,
            ),
          ),
          SizedBox(
            height: 0.025 * widget.size.height,
          ),
          SizedBox(
            width: 0.8 * widget.size.width,
            child: TextFormField(
              controller: _new1Controller,
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return AppLocalizations.of(context)!.requiredField;
                }
                return null;
              },
              decoration: InputDecoration(
                hintText: AppLocalizations.of(context)!.newPassword,
                prefixIcon: Icon(Icons.password),
                filled: true,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10.0),
                  borderSide: BorderSide(
                    color: Color(0xFF737373),
                  ),
                ),
                fillColor: Colors.white.withOpacity(0.35),
              ),
              obscureText: true,
            ),
          ),
          SizedBox(
            height: 0.025 * widget.size.height,
          ),
          SizedBox(
            width: 0.8 * widget.size.width,
            child: TextFormField(
              controller: _new2Controller,
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return AppLocalizations.of(context)!.requiredField;
                } else if (_new1Controller.text != _new2Controller.text) {
                  return AppLocalizations.of(context)!.passwordsDoNotMatch;
                }
                return null;
              },
              decoration: InputDecoration(
                hintText: AppLocalizations.of(context)!.confirmNewPassword,
                prefixIcon: Icon(Icons.password),
                filled: true,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10.0),
                  borderSide: BorderSide(
                    color: Color(0xFF737373),
                  ),
                ),
                fillColor: Colors.white.withOpacity(0.35),
              ),
              obscureText: true,
            ),
          ),
          SizedBox(
            height: 0.025 * widget.size.height,
          ),
          SizedBox(
            width: 0.8 * widget.size.width,
            height: 50,
            child: TextButton(
              onPressed: () async {
                if (_formKey.currentState!.validate()) {
                  bool oldPasswordCorrect =
                      await AuthApiClient.checkPassword(_oldController.text);
                  if (!oldPasswordCorrect) {
                    SnackBar sentSnack = SnackBar(
                      content: Text(
                          AppLocalizations.of(context)!.incorrectOldPassword),
                    );
                    ScaffoldMessenger.of(context).showSnackBar(sentSnack);
                    return;
                  }

                  await AuthApiClient.changePassword(
                    _new1Controller.text,
                    _new2Controller.text,
                    context,
                  );
                }
              },
              child: Text(
                AppLocalizations.of(context)!.changePassword,
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Colors.white,
                    fontSize: 17.5,
                  ),
                ),
              ),
              style: ButtonStyle(
                elevation: WidgetStateProperty.all(8),
                shadowColor: WidgetStateProperty.all(
                  Colors.black.withOpacity(0.5),
                ),
                shape: WidgetStateProperty.all<RoundedRectangleBorder>(
                  RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(15.0),
                  ),
                ),
                backgroundColor: WidgetStateProperty.all(
                  Color(0xFFDC4654),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _oldController.dispose();
    _new1Controller.dispose();
    _new2Controller.dispose();
    super.dispose();
  }
}
