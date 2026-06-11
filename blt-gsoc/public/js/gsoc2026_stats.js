(function () {
    function num(value) {
        return Number.isFinite(value) ? String(value) : '-';
    }

    function makePill(iconClass, label, value) {
        var pill = document.createElement('span');
        pill.className = 'project-stat-pill';
        pill.innerHTML =
            '<i class="' + iconClass + '" aria-hidden="true"></i>' +
            '<span class="project-stat-label">' + label + '</span>' +
            '<span class="project-stat-value">' + value + '</span>';
        return pill;
    }

    var payload = window.GSOC2026_STATS || {};
    var projects = payload.projects || {};
    var cards = document.querySelectorAll('#gsoc-student-cards article[data-project-id], #intern-cards article[data-project-id]');

    cards.forEach(function (card) {
        var projectId = card.getAttribute('data-project-id');
        var data = projects[projectId];
        var line = card.querySelector('.project-compact-stats');

        if (!line) {
            line = document.createElement('div');
            line.className = 'project-compact-stats';
            card.appendChild(line);
        }

        line.innerHTML = '';

        var statsRow = document.createElement('div');
        statsRow.className = 'project-stat-pills';

        if (!data) {
            statsRow.appendChild(makePill('fa-solid fa-code-pull-request', 'PR', '-/-'));
            statsRow.appendChild(makePill('fa-solid fa-circle-dot', 'Issue', '-/-'));
            statsRow.appendChild(makePill('fa-solid fa-code-commit', 'Commit', '-'));
            statsRow.appendChild(makePill('fa-solid fa-user', 'User', 'PR- IC-'));
            line.appendChild(statsRow);
            return;
        }

        var repo = data.repoStats || {};
        var userStats = data.userStats || {};
        var userBits = Object.keys(userStats).map(function (login) {
            var user = userStats[login] || {};
            return login + ' PR' + num(user.prTotal) + ' IC' + num(user.closedIssues);
        });

        var compactUser = userBits.length > 0 ? userBits.join(', ') : 'PR- IC-';

        statsRow.appendChild(makePill('fa-solid fa-code-pull-request', 'PR', num(repo.openPR) + '/' + num(repo.mergedPR)));
        statsRow.appendChild(makePill('fa-solid fa-circle-dot', 'Issue', num(repo.openIssues) + '/' + num(repo.closedIssues)));
        statsRow.appendChild(makePill('fa-solid fa-code-commit', 'Commit', num(repo.totalCommits)));
        statsRow.appendChild(makePill('fa-solid fa-user', 'User', compactUser));

        line.appendChild(statsRow);
    });
})();
