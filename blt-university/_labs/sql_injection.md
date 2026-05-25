---
layout: lab
title: SQL Injection
description: Learn SQL injection through interactive security exercises.
difficulty: beginner
category: Web Security
estimated_time: 60

tasks:
  - name: Introduction to SQL Injection
    description: Learn the basics of SQL injection vulnerabilities and how they occur.
    type: theory
    order: 1
    heading: What is SQL Injection?
    content: |
      SQL injection is a code injection technique that exploits a security vulnerability in an application's software. The vulnerability occurs when user input is not safely validated, escaped, typed, or parameterized before it becomes part of a SQL query.

      ### How SQL Injection Works

      SQL injection attacks work by inserting malicious SQL code into application queries. When the application executes these modified queries, it can result in:

      - Unauthorized access to data
      - Data theft or modification
      - Authentication bypass
      - Complete system compromise

      ### Example Vulnerable Code

      ```java
      String query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'";
      ```
    mcq:
      question: What makes an application vulnerable to SQL injection?
      options:
        - A) Improper input validation and sanitization
        - B) Using strong passwords
        - C) Having too many database tables
        - D) Using encrypted connections
      answer: A

  - name: Identifying SQL Injection Points
    description: Learn how to identify potential SQL injection vulnerabilities in web applications.
    type: theory
    order: 2
    heading: Finding SQL Injection Vulnerabilities
    content: |
      SQL injection vulnerabilities can appear anywhere untrusted data is used to build database queries.

      ### Common Injection Points

      - **Login forms:** Username and password fields
      - **Search boxes:** Query parameters
      - **URL parameters:** GET request parameters
      - **Form inputs:** POST request data
      - **Cookies:** Session data
      - **HTTP headers:** User-Agent, Referer, and similar values

      ### Testing Techniques

      Use these payloads to test for SQL injection:

      - Single quote (`'`) to look for database errors
      - Double quote (`"`) as an alternate string delimiter
      - SQL comments (`--` or `/*`) to comment out the rest of a query
      - Boolean conditions (`1=1`, `1=2`) to test logic manipulation
    mcq:
      question: Which of the following is NOT a common SQL injection testing payload?
      options:
        - A) Single quote (')
        - B) Boolean condition (1=1)
        - C) HTML tags (<script>)
        - D) SQL comment (--)
      answer: C

  - name: Basic SQL Injection - Login Bypass
    description: Practice bypassing login authentication using SQL injection.
    type: simulation
    order: 3
    simulation:
      type: login_bypass
      scenario: vulnerable_login
      target_url: /vulnerable-login
      vulnerable_parameters:
        - username
        - password
      success_payload: "admin' -- -"
      success_criteria: Successfully logged in as admin without knowing the password.
      hints:
        - Try using SQL comments to bypass the password check.
        - The application uses single quotes around the username.
        - Remember that -- followed by whitespace comments out the rest of the SQL query.

  - name: Union-Based SQL Injection
    description: Learn about Union-based SQL injection attacks to extract data.
    type: theory
    order: 4
    heading: Union-Based SQL Injection
    content: |
      Union-based SQL injection leverages the `UNION` SQL operator to combine the results of two or more `SELECT` statements into a single result.

      ### Requirements for UNION Attacks

      - The same number of columns in both `SELECT` statements
      - Compatible data types in corresponding columns
      - Application output that displays query results

      ### Finding Column Count

      Use `ORDER BY` to determine the number of columns:

      ```sql
      ' ORDER BY 1-- -
      ' ORDER BY 2-- -
      ' ORDER BY 3-- -
      ```

      ### Union Attack Example

      ```sql
      ' UNION SELECT username, password FROM users-- -
      ```
    mcq:
      question: What is required for a successful UNION-based SQL injection?
      options:
        - A) The application must be written in PHP
        - B) Same number of columns and compatible data types
        - C) The database must be MySQL
        - D) The user must have admin privileges
      answer: B

  - name: Union Attack - Data Extraction
    description: Practice extracting sensitive data using Union-based SQL injection.
    type: simulation
    order: 5
    simulation:
      type: union_injection
      scenario: data_extraction
      target_url: /vulnerable-search
      vulnerable_parameters:
        - search
      table_structure:
        users:
          - id
          - username
          - password
          - email
        products:
          - id
          - name
          - price
          - description
      success_payload: "' UNION SELECT id, username, password, email FROM users-- -"
      success_criteria: Extract all usernames and passwords from users table.
      hints:
        - First determine the number of columns using ORDER BY.
        - Use UNION SELECT to combine with your malicious query.
        - The original query selects 4 columns from the products table.

  - name: Boolean-Based Blind SQL Injection
    description: Learn about blind SQL injection when no data is returned directly.
    type: theory
    order: 6
    heading: Boolean-Based Blind SQL Injection
    content: |
      Blind SQL injection occurs when an application is vulnerable to SQL injection, but HTTP responses do not contain query results or database errors.

      ### Characteristics

      - No direct database output in the response
      - Application behavior changes based on query truth
      - Requires inference techniques
      - Time-consuming but effective

      ### Testing Technique

      Use conditional statements to infer information:

      ```sql
      ' AND 1=1-- -     -- Should return normal response
      ' AND 1=2-- -     -- Should return different response
      ```

      ### Data Extraction Example

      ```sql
      ' AND (SELECT SUBSTRING(username,1,1) FROM users WHERE id=1)='a'-- -
      ```
    mcq:
      question: In Boolean-based blind SQL injection, how do you extract data?
      options:
        - A) By reading error messages
        - B) By analyzing response differences for true/false conditions
        - C) By viewing database tables directly
        - D) By measuring response timing only
      answer: B

  - name: Blind SQL Injection - Character Extraction
    description: Practice extracting data character by character using blind techniques.
    type: simulation
    order: 7
    simulation:
      type: blind_injection
      scenario: character_extraction
      target_url: /vulnerable-profile
      vulnerable_parameters:
        - user_id
      blind_type: boolean
      target_data: admin_password
      success_payload: "' AND (SELECT SUBSTRING(password,1,1) FROM users WHERE username='admin')='p'-- -"
      success_criteria: Extract the first 5 characters of the admin password.
      expected_approach: Boolean-based character-by-character extraction.
      hints:
        - Use AND conditions to test character values.
        - Compare response content for true/false conditions.
        - Use SUBSTRING or SUBSTR to extract individual characters.
        - ASCII values can help with character comparison.

  - name: Time-Based Blind SQL Injection
    description: Learn about time-based blind SQL injection techniques.
    type: theory
    order: 8
    heading: Time-Based Blind SQL Injection
    content: |
      Time-based blind SQL injection is used when Boolean-based techniques do not work. It relies on injecting SQL queries that cause the database to wait for a specified amount of time.

      ### Common Time Functions

      - **MySQL:** `SLEEP(5)`
      - **PostgreSQL:** `pg_sleep(5)`
      - **SQL Server:** `WAITFOR DELAY '00:00:05'`
      - **Oracle:** `dbms_pipe.receive_message(('a'),5)`

      ### Testing Example

      ```sql
      ' AND IF(1=1, SLEEP(5), 0)-- -
      ' AND IF((SELECT COUNT(*) FROM users)>5, SLEEP(5), 0)-- -
      ```

      ### Data Extraction

      ```sql
      ' AND IF((SELECT SUBSTRING(password,1,1) FROM users WHERE username='admin')='p', SLEEP(5), 0)-- -
      ```
    mcq:
      question: What is the main indicator of successful time-based SQL injection?
      options:
        - A) Error messages in the response
        - B) Changed content in the response
        - C) Increased response time
        - D) HTTP status code changes
      answer: C

  - name: Time-Based Attack Simulation
    description: Practice time-based blind SQL injection to extract sensitive information.
    type: simulation
    order: 9
    simulation:
      type: time_based_injection
      scenario: password_extraction
      target_url: /vulnerable-news
      vulnerable_parameters:
        - article_id
      database_type: mysql
      time_function: SLEEP
      target_data: admin_password_length
      success_payload: "' AND IF((SELECT LENGTH(password) FROM users WHERE username='admin')=8, SLEEP(5), 0)-- -"
      success_criteria: Determine the length of the admin password using time delays.
      hints:
        - Use SLEEP(5) to create time delays.
        - Test different password lengths using LENGTH() function.
        - Measure response times to detect successful conditions.
        - A 5-second delay indicates a true condition.

  - name: Advanced SQL Injection Prevention
    description: Learn comprehensive strategies to prevent SQL injection attacks.
    type: theory
    order: 10
    heading: SQL Injection Prevention
    content: |
      Preventing SQL injection requires a multi-layered approach combining secure coding practices and proper application architecture.

      ### Primary Defense: Prepared Statements

      ```java
      String query = "SELECT * FROM users WHERE username = ? AND password = ?";
      PreparedStatement stmt = connection.prepareStatement(query);
      stmt.setString(1, username);
      stmt.setString(2, password);
      ```

      ### Additional Defenses

      - **Input validation:** Whitelist allowed characters
      - **Stored procedures:** When properly implemented
      - **Escaping:** As a secondary defense
      - **Least privilege:** Minimal database permissions
      - **WAF:** Web Application Firewall

      ### Best Practices

      - Never trust user input
      - Use parameterized queries exclusively
      - Implement proper error handling
      - Run regular security testing
      - Keep software updated
    mcq:
      question: What is the most effective primary defense against SQL injection?
      options:
        - A) Input validation and filtering
        - B) Using a Web Application Firewall
        - C) Prepared statements with parameterized queries
        - D) Encrypting database connections
      answer: C
---
