package com.tinpham.nflpredictor.dto;

import com.tinpham.nflpredictor.model.Team;
import com.tinpham.nflpredictor.model.TeamForm;

public record TeamDetails(Team team, TeamForm form, Standing standing) {
}
