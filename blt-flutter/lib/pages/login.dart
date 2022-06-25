import 'package:flutter/material.dart';
import '../data/user.dart';
import '../providers/auth.dart';
import '../providers/user_provider.dart';
//import '../util/validators.dart';
import '../routes/routing.dart';
import '../util/widgets.dart';
import 'package:provider/provider.dart';
import 'home.dart';

class Login extends StatefulWidget {
  const Login({Key? key}) : super(key: key);

  @override
  _LoginState createState() => _LoginState();
}

class _LoginState extends State<Login> {
  final formKey = new GlobalKey<FormState>();

  late String _username, _password, _email;

  @override
  Widget build(BuildContext context) {
    AuthProvider auth = Provider.of<AuthProvider>(context);

    final usernameField = TextFormField(
      autofocus: false,
      validator: (value) => value!.isEmpty ? "Please enter username" : null,
      onSaved: (value) => _username = value!,
      decoration: buildInputDecoration("Confirm username", Icons.person),
    );

    final emailField = TextFormField(
      autofocus: false,
      validator: (value) => value!.isEmpty ? "Please enter email" : null,
      onSaved: (value) => _email = value!,
      decoration: buildInputDecoration("Confirm email", Icons.email),
    );

    final passwordField = TextFormField(
      autofocus: false,
      obscureText: true,
      validator: (value) => value!.isEmpty ? "Please enter password" : null,
      onSaved: (value) => _password = value!,
      decoration: buildInputDecoration("Confirm password", Icons.lock),
    );

    var loading = Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: <Widget>[
        CircularProgressIndicator(),
        Text(" Authenticating ... Please wait")
      ],
    );

    final forgotLabel = Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: <Widget>[
        TextButton(
          child: Text("Forgot password?",
              style: TextStyle(fontWeight: FontWeight.w300)),
          onPressed: () {},
        ),
        TextButton(
          child: Text("Sign up", style: TextStyle(fontWeight: FontWeight.w300)),
          onPressed: () {},
        ),
      ],
    );

    var doLogin = () {
      final form = formKey.currentState;

      if (form != null && form.validate()) {
        form.save();
        final Future<Map<String, dynamic>> successfulMessage =
            auth.login(_username, _password, _email);

        successfulMessage.then((response) {
          if (response['status']) {
            User user = response['user'];
            print(response['user']);
            Provider.of<UserProvider>(context, listen: false).setUser(user);
            Navigator.of(context).pushNamed(
              RouteManager.homePage,
            ); //Navigator.pushReplacementNamed(context, '/dashboard');
            //
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(response['message'][0]),
              ),
            );
          }
        });
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("form is invalid"),
          ),
        );
        print("form is invalid");
      }
    };

    return SafeArea(
      child: Scaffold(
        body: Container(
          padding: EdgeInsets.all(40.0),
          child: Form(
            key: formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                label("Username"),
                SizedBox(height: 5.0),
                usernameField,
                label("Email"),
                SizedBox(height: 5.0),
                emailField,
                label("Password"),
                SizedBox(height: 5.0),
                passwordField,
                SizedBox(height: 20.0),
                auth.loggedInStatus == Status.Authenticating
                    ? loading
                    : ElevatedButton(
                        onPressed: () {
                          doLogin();
                        },
                        child: Text('Log In'),
                      ),
                SizedBox(height: 5.0),
                forgotLabel
              ],
            ),
          ),
        ),
      ),
    );
  }
}
