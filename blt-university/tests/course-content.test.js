const fs = require('node:fs');
const path = require('node:path');

const coursesDirectory = path.join(__dirname, '..', '_courses');

function courseFiles() {
  return fs.readdirSync(coursesDirectory).filter(file => file.endsWith('.md')).sort();
}

function courseSource(file) {
  return fs.readFileSync(path.join(coursesDirectory, file), 'utf8');
}

describe('focused course catalog', () => {
  it('contains only the five approved learning paths', () => {
    expect(courseFiles()).toEqual([
      'advanced-pentesting.md',
      'cloud-security-essentials.md',
      'crypto-for-devs.md',
      'cybersecurity-foundations.md',
      'web-security-intro.md'
    ]);
  });

  it('maps every existing lab into a concise foundation course', () => {
    const foundationCourses = [
      courseSource('cybersecurity-foundations.md'),
      courseSource('web-security-intro.md')
    ].join('\n');
    const labFiles = fs.readdirSync(path.join(__dirname, '..', '_labs'))
      .filter(file => file.endsWith('.md'));

    labFiles.forEach(file => {
      const slug = file.replace(/\.md$/, '');
      expect(foundationCourses).toContain(`- ${slug}`);
    });
  });

  it.each([
    ['advanced-pentesting.md', ['type: choice', 'type: console', 'type: artifact', 'type: sequence']],
    ['cloud-security-essentials.md', ['type: artifact', 'type: inspect', 'type: sequence', 'type: choice']],
    ['crypto-for-devs.md', ['type: artifact', 'type: sequence', 'type: choice']]
  ])('gives every lesson in %s a purposeful activity', (file, challengeTypes) => {
    const source = courseSource(file);

    expect(source.match(/^    challenge:/gm)).toHaveLength(5);
    challengeTypes.forEach(challengeType => expect(source).toContain(challengeType));
  });

  it('describes the learning outcomes for every course', () => {
    courseFiles().forEach(file => {
      const source = courseSource(file);
      expect(source).toContain('outcomes:');
      expect(source.match(/^  - /gm).length).toBeGreaterThanOrEqual(3);
    });

    const layout = fs.readFileSync(path.join(__dirname, '..', '_layouts', 'course.html'), 'utf8');
    expect(layout).toContain('By the end of this course, you can');
    expect(layout).toContain('{{ page.lessons.size }} lessons');
  });

  it('connects the recommended course sequence without hard-coded layout links', () => {
    expect(courseSource('cybersecurity-foundations.md')).toContain('next_course: web-security-intro');
    expect(courseSource('web-security-intro.md')).toContain('next_course: advanced-pentesting');
    expect(courseSource('advanced-pentesting.md')).toContain('next_course: cloud-security-essentials');
    expect(courseSource('cloud-security-essentials.md')).toContain('next_course: crypto-for-devs');

    const layout = fs.readFileSync(path.join(__dirname, '..', '_layouts', 'course.html'), 'utf8');
    expect(layout).toContain('site.courses | where: "slug", page.next_course | first');
    expect(layout).toContain('data-next-course');
  });
});
