import { Component, DestroyRef, inject } from "@angular/core";
import { NgIf } from "@angular/common";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { TranslateModule, TranslateService } from "@ngx-translate/core";
import {
  AppSettingsService,
  UI_LANGUAGES,
  UiLanguage,
} from "../../_services/app-settings.service";
import {
  FlwSelectComponent,
  FlwSelectOption,
} from "../../ui/select/flw-select.component";
import { FlwTab, FlwTabsComponent } from "../../ui/tabs/flw-tabs.component";
@Component({
  standalone: true,
  imports: [NgIf, TranslateModule, FlwSelectComponent, FlwTabsComponent],
  templateUrl: "./settings.component.html",
  styleUrl: "./settings.component.css",
})
export class SettingsComponent {
  private destroyRef = inject(DestroyRef);
  tabs: FlwTab[] = [];
  active = "general";
  language: UiLanguage;
  languageOptions: FlwSelectOption[] = [];
  constructor(
    private settings: AppSettingsService,
    private translate: TranslateService,
  ) {
    this.language = settings.getLanguage();
    this.buildLabels();
    translate.onLangChange
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.buildLabels());
  }
  changeLanguage(language: UiLanguage) {
    this.language = language;
    this.settings.setLanguage(language);
    this.translate.use(language);
  }
  private buildLabels() {
    this.tabs = ["general", "backend"].map((id) => ({
      id,
      label: this.translate.instant(`SETTINGS.TABS.${id.toUpperCase()}`),
    }));
    this.languageOptions = UI_LANGUAGES.map((value) => ({
      value,
      label: this.translate.instant(`SETTINGS.LANGUAGE.${value.toUpperCase()}`),
    }));
  }
}
