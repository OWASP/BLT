const fs = require('node:fs');
const path = require('node:path');

const labsDirectory = path.join(__dirname, '..', '_labs');
const coursesDirectory = path.join(__dirname, '..', '_courses');
const supportedTracks = new Set(['professional', 'hygiene', 'both']);

function labFiles() {
  return fs.readdirSync(labsDirectory).filter((file) => file.endsWith('.md')).sort();
}

function trackFromFrontmatter(file) {
  const source = fs.readFileSync(path.join(labsDirectory, file), 'utf8');
  const frontmatter = source.match(/^---\n([\s\S]*?)\n---/);
  const track = frontmatter && frontmatter[1].match(/^track:\s*(\S+)\s*$/m);

  return track ? track[1] : undefined;
}

function courseSource(file) {
  return fs.readFileSync(path.join(coursesDirectory, file), 'utf8');
}

describe('lab learning tracks', () => {
  it('declares a supported track for every lab', () => {
    const files = labFiles();

    expect(files.length).toBeGreaterThan(0);
    files.forEach((file) => {
      expect(supportedTracks.has(trackFromFrontmatter(file))).toBe(true);
    });
  });

  it('provides beginner and professional courses for the two audiences', () => {
    const hygieneCourse = courseSource('cybersecurity-foundations.md');
    const professionalCourse = courseSource('web-security-intro.md');

    expect(hygieneCourse).toMatch(/level: Beginner/);
    expect(hygieneCourse).toMatch(/track: hygiene/);
    expect(hygieneCourse).toMatch(/- phishing-awareness/);
    expect(hygieneCourse).toMatch(/- passwords-and-mfa/);
    expect(hygieneCourse).toMatch(/- safe-browsing-and-downloads/);
    expect(professionalCourse).toMatch(/level: Beginner/);
    expect(professionalCourse).toMatch(/track: professional/);
    expect(professionalCourse).toMatch(/- sql_injection/);
    expect(professionalCourse).toMatch(/- server_side_request_forgery/);
  });

  it('keeps the initial Cyber Hygiene lab set beginner-friendly', () => {
    const hygieneLabs = labFiles().filter(file => trackFromFrontmatter(file) === 'hygiene');

    expect(hygieneLabs).toEqual([
      'passwords-and-mfa.md',
      'phishing-awareness.md',
      'safe-browsing-and-downloads.md'
    ]);
    hygieneLabs.forEach(file => {
      const source = fs.readFileSync(path.join(labsDirectory, file), 'utf8');
      expect(source).toMatch(/^difficulty:\s*beginner\s*$/m);
    });
  });
});
