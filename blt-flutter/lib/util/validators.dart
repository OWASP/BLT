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
