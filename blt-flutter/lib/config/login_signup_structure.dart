class LoginFreshWords {
  String loginWith;
  String login;
  String exploreApp;
  String notAccount;
  String signUp;
  String textLoading;
  String hintLoginUser;
  String hintLoginPassword;
  String hintSignUpRepeatPassword;
  String hintName;
  String hintSurname;

  String recoverPassword;

  String messageRecoverPassword;

  LoginFreshWords(
      {this.loginWith = 'Login With',
      this.hintName = 'Name',
      this.hintSurname = 'Surname',
      this.hintSignUpRepeatPassword = 'Repeat Password',
      this.hintLoginPassword = 'Password',
      this.recoverPassword = 'Recover Password',
      this.messageRecoverPassword =
          'To recover the password, enter the email and press send email, you will receive an email so you can update your password. Only available for accounts created by username and password',
      this.hintLoginUser = 'Username or email',
      this.login = 'Login',
      this.exploreApp = 'Explore App',
      this.notAccount = 'You dot not have an account?',
      this.signUp = 'Sign Up',
      this.textLoading = 'please wait ...'});
}
