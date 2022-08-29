String? validateEmail(String? value) {
  RegExp regex = new RegExp(
      r'^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$');
  if (value == null || value.isEmpty) {
    return "Your email is required";
  } else if (!regex.hasMatch(value)) {
    return "Please provide a valid emal address";
  }
  return null;
}

String? validatePassword(String? value) {
  RegExp regex = new RegExp(
      r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{8,20}$');
  if (value == null || value.isEmpty) {
    return "Your Password is required";
  } else if (!regex.hasMatch(value)) {
    return "Please provide a valid Password!\n1. Password length should be in range (8, 20)\n2. Password must contain atleast a LowerCase Letter\n3.Password must contain atleast a UpperCase Leter\n4.Password must contain atleast a numerical digit\n5.Password must contain atleast a special character \n(\$, @, #, %)";
  }
  return null;
}
