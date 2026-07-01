const {
  cloneSerializableValue,
  loadLabHelpers
} = require('./helpers');

function checkResults(result) {
  return cloneSerializableValue(result.checks.map((check) => check.passed));
}

describe('lab fix validators', () => {
  describe('answer validation helpers', () => {
    describe.each([
      {
        name: 'same lines in different order',
        selectedLines: [3, 2],
        expectedLines: [2, 3],
        expected: true
      },
      {
        name: 'string line numbers',
        selectedLines: ['3', '2'],
        expectedLines: [2, 3],
        expected: true
      },
      {
        name: 'missing vulnerable line',
        selectedLines: [2],
        expectedLines: [2, 3],
        expected: false
      },
      {
        name: 'extra selected line',
        selectedLines: [2, 3, 4],
        expectedLines: [2, 3],
        expected: false
      }
    ])('line selection: $name', ({ selectedLines, expectedLines, expected }) => {
      it(`returns ${expected}`, () => {
        const { validateLineSelection } = loadLabHelpers().helpers;

        expect(validateLineSelection(selectedLines, expectedLines)).toBe(expected);
      });
    });

    describe.each([
      {
        name: 'correct answer id',
        selectedAnswer: 'direct_sql_input',
        expectedAnswer: 'direct_sql_input',
        expected: true
      },
      {
        name: 'wrong answer id',
        selectedAnswer: 'missing_https',
        expectedAnswer: 'direct_sql_input',
        expected: false
      },
      {
        name: 'numeric ids with matching values',
        selectedAnswer: 2,
        expectedAnswer: '2',
        expected: true
      },
      {
        name: 'empty selected answer',
        selectedAnswer: '',
        expectedAnswer: 'direct_sql_input',
        expected: false
      }
    ])('explanation answer: $name', ({ selectedAnswer, expectedAnswer, expected }) => {
      it(`returns ${expected}`, () => {
        const { validateExplainAnswer } = loadLabHelpers().helpers;

        expect(validateExplainAnswer(selectedAnswer, expectedAnswer)).toBe(expected);
      });
    });
  });

  describe('SQL injection fixes', () => {
    const bypassConfig = { attack_payloads: ["' OR '1'='1"] };

    describe.each([
      {
        name: 'question mark placeholders with array-bound values',
        code: `
          const query = 'SELECT * FROM users WHERE username = ? AND password = ?';
          db.execute(query, [username, password]);
        `
      },
      {
        name: 'PostgreSQL placeholders with array-bound values',
        code: `
          const query = 'SELECT * FROM users WHERE username = $1 AND password = $2';
          db.query(query, [username, password]);
        `
      },
      {
        name: 'named placeholders with explicit parameter binding',
        code: `
          const statement = db.prepare(
            'SELECT * FROM users WHERE username = :username AND password = :password'
          );
          statement.bindValue(':username', username);
          statement.bindValue(':password', password);
        `
      }
    ])('accepted secure pattern: $name', ({ code }) => {
      it('passes every SQLi validation check', () => {
        const { validateSqliFix } = loadLabHelpers().helpers;
        const result = validateSqliFix(code, bypassConfig);

        expect(result.passed).toBe(true);
        expect(checkResults(result)).toEqual([true, true, true, true]);
      });
    });

    describe.each([
      {
        name: 'direct string concatenation in SQL',
        code: `
          const query = "SELECT * FROM users WHERE username = '" + username + "'";
          db.query(query);
        `,
        expectedChecks: [false, false, false, false]
      },
      {
        name: 'SQL variable assembled across statements',
        code: `
          const baseQuery = 'SELECT * FROM users WHERE id = ';
          const query = baseQuery + userId;
          db.query(query);
        `,
        expectedChecks: [false, false, false, false]
      },
      {
        name: 'template literal interpolation',
        code: `
          const query = \`SELECT * FROM profiles WHERE user_id = \${userId}\`;
          db.query(query);
        `,
        expectedChecks: [false, false, false, false]
      },
      {
        name: 'multiline template literal interpolation',
        code: `
          const query = \`
            SELECT * FROM users
            WHERE id = \${userId}
          \`;
          db.query(query);
        `,
        expectedChecks: [false, false, false, false]
      },
      {
        name: 'placeholders without bound values',
        code: `
          const query = 'SELECT * FROM users WHERE username = ? AND password = ?';
          db.query(query);
        `,
        expectedChecks: [true, true, false, true]
      },
      {
        name: 'empty code submission',
        code: '',
        expectedChecks: [true, false, false, true]
      }
    ])('rejected unsafe pattern: $name', ({ code, expectedChecks }) => {
      it('fails closed with targeted check results', () => {
        const { validateSqliFix } = loadLabHelpers().helpers;
        const result = validateSqliFix(code, bypassConfig);

        expect(result.passed).toBe(false);
        expect(checkResults(result)).toEqual(expectedChecks);
      });
    });

    it('does not reject unrelated string concatenation outside a SQL statement', () => {
      const { validateSqliFix } = loadLabHelpers().helpers;
      const result = validateSqliFix(`
        const query = 'SELECT * FROM users WHERE id = ?';
        logger.info('loading user=' + userId);
        db.execute(query, [userId]);
      `);

      expect(result.passed).toBe(true);
    });

    it('does not split SQL statements on semicolons inside string literals', () => {
      const { validateSqliFix } = loadLabHelpers().helpers;
      const result = validateSqliFix(`
        const query = 'SELECT * FROM log WHERE msg = "event;type" AND user_id = ?';
        logger.info('loading user=' + userId);
        db.execute(query, [userId]);
      `);

      expect(result.passed).toBe(true);
    });
  });

  describe('XSS fixes', () => {
    const executablePayloadConfig = {
      attack_payloads: ["<img src=x onerror=alert('XSS')>"]
    };

    describe.each([
      {
        name: 'textContent assignment',
        code: `
          const comment = request.query.comment;
          preview.textContent = comment;
        `
      },
      {
        name: 'createTextNode rendering',
        code: `
          const comment = request.query.comment;
          preview.appendChild(document.createTextNode(comment));
        `
      },
      {
        name: 'encoded value before innerHTML',
        code: `
          const comment = request.query.comment;
          preview.innerHTML = escapeHTML(comment);
        `
      },
      {
        name: 'sanitized value before innerHTML',
        code: `
          const comment = request.query.comment;
          preview.innerHTML = DOMPurify.sanitize(comment);
        `
      }
    ])('accepted secure pattern: $name', ({ code }) => {
      it('passes XSS validation', () => {
        const { validateXssFix } = loadLabHelpers().helpers;
        const result = validateXssFix(code, executablePayloadConfig);

        expect(result.passed).toBe(true);
        expect(checkResults(result)).toEqual([true, true, true]);
      });
    });

    describe.each([
      {
        name: 'raw innerHTML assignment',
        code: `
          const comment = request.query.comment;
          preview.innerHTML = comment;
        `
      },
      {
        name: 'raw outerHTML assignment',
        code: 'preview.outerHTML = request.query.comment;'
      },
      {
        name: 'insertAdjacentHTML with attacker-controlled data',
        code: "result.insertAdjacentHTML('beforeend', request.query.search);"
      },
      {
        name: 'document.write with URL-controlled data',
        code: 'document.write(location.hash);'
      },
      {
        name: 'empty code submission',
        code: ''
      }
    ])('rejected unsafe pattern: $name', ({ code }) => {
      it('fails XSS validation', () => {
        const { validateXssFix } = loadLabHelpers().helpers;
        const result = validateXssFix(code, executablePayloadConfig);

        expect(result.passed).toBe(false);
      });
    });
  });

  describe('CSRF fixes', () => {
    describe.each([
      {
        name: 'token verification before update with Lax cookie',
        code: `
          app.use(session({ cookie: { sameSite: 'Lax' } }));
          app.post('/profile/update', requireLogin, (req, res) => {
            verifyCsrfToken(req.body.csrf_token, req.session.csrf_token);
            updateEmail(req.user.id, req.body.email);
            res.redirect('/profile');
          });
        `
      },
      {
        name: 'token comparison before delegated save with Strict cookie',
        code: `
          app.use(session({ cookie: { sameSite: 'Strict' } }));
          app.post('/settings', requireLogin, (req, res) => {
            compareCsrfToken(req.body.csrf_token, req.session.csrf_token);
            settingsService.saveUserSettings(req.user.id, req.body.settings);
            res.redirect('/settings');
          });
        `
      }
    ])('accepted secure pattern: $name', ({ code }) => {
      it('passes every CSRF validation check', () => {
        const { validateCsrfFix } = loadLabHelpers().helpers;
        const result = validateCsrfFix(code);

        expect(result.passed).toBe(true);
        expect(checkResults(result)).toEqual([true, true, true, true]);
      });
    });

    describe.each([
      {
        name: 'token is read but never verified',
        code: `
          app.post('/profile/update', requireLogin, (req, res) => {
            const csrf_token = req.body.csrf_token;
            updateEmail(req.user.id, req.body.email);
            res.redirect('/profile');
          });
        `,
        expectedChecks: [true, false, false, false]
      },
      {
        name: 'token is verified after state changes',
        code: `
          app.use(session({ cookie: { sameSite: 'Strict' } }));
          app.post('/profile/update', requireLogin, (req, res) => {
            updateEmail(req.user.id, req.body.email);
            verifyCsrfToken(req.body.csrf_token, req.session.csrf_token);
            res.redirect('/profile');
          });
        `,
        expectedChecks: [true, true, false, true]
      },
      {
        name: 'delegated update happens before token verification',
        code: `
          app.use(session({ cookie: { sameSite: 'Strict' } }));
          app.post('/profile/update', requireLogin, (req, res) => {
            helpers.performUpdate(req.user.id, req.body.email);
            verifyCsrfToken(req.body.csrf_token, req.session.csrf_token);
            res.redirect('/profile');
          });
        `,
        expectedChecks: [true, true, false, true]
      },
      {
        name: 'SameSite cookie is the only defense',
        code: `
          app.use(session({ cookie: { sameSite: 'Lax' } }));
          app.post('/profile/update', requireLogin, (req, res) => {
            updateEmail(req.user.id, req.body.email);
            res.redirect('/profile');
          });
        `,
        expectedChecks: [false, false, false, true]
      },
      {
        name: 'GET route performs destructive action',
        code: `
          app.get('/account/delete', requireLogin, (req, res) => {
            deleteAccount(req.user.id);
            res.redirect('/');
          });
        `,
        expectedChecks: [false, false, false, false]
      }
    ])('rejected unsafe pattern: $name', ({ code, expectedChecks }) => {
      it('fails closed with targeted check results', () => {
        const { validateCsrfFix } = loadLabHelpers().helpers;
        const result = validateCsrfFix(code);

        expect(result.passed).toBe(false);
        expect(checkResults(result)).toEqual(expectedChecks);
      });
    });
  });
});
