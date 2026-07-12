import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { FormControl, ReactiveFormsModule } from "@angular/forms";
import { FlwSelectComponent } from "./select/flw-select.component";
import { FlwSwitchComponent } from "./switch/flw-switch.component";
import { FlwTagInputComponent } from "./tag-input/flw-tag-input.component";

@Component({
  standalone: true,
  imports: [
    ReactiveFormsModule,
    FlwSelectComponent,
    FlwSwitchComponent,
    FlwTagInputComponent,
  ],
  template: `<flw-switch [formControl]="enabled" /><flw-select
      [formControl]="choice"
      [options]="options"
    /><flw-tag-input [formControl]="tags" [options]="options" />`,
})
class HostComponent {
  enabled = new FormControl(false, { nonNullable: true });
  choice = new FormControl<string | number>("a", { nonNullable: true });
  tags = new FormControl<Array<string | number>>([], { nonNullable: true });
  options = [
    { label: "Alpha", value: "a" },
    { label: "Beta", value: "b" },
  ];
}

describe("Flowless form controls", () => {
  let fixture: ComponentFixture<HostComponent>;
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });
  it("writes values from reactive forms", () => {
    fixture.componentInstance.enabled.setValue(true);
    fixture.componentInstance.choice.setValue("b");
    fixture.componentInstance.tags.setValue(["a"]);
    fixture.detectChanges();
    expect(
      fixture.nativeElement.querySelector("input[type=checkbox]").checked,
    ).toBeTrue();
    expect(fixture.nativeElement.querySelector("select").value).toBe("1");
    expect(fixture.nativeElement.querySelector(".tag").textContent).toContain(
      "Alpha",
    );
  });
  it("propagates user changes", () => {
    const checkbox = fixture.nativeElement.querySelector(
      "input[type=checkbox]",
    );
    checkbox.click();
    expect(fixture.componentInstance.enabled.value).toBeTrue();
  });
});
